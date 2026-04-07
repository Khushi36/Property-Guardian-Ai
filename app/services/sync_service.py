import uuid
import logging

from sqlalchemy.orm import Session

from app.core.chroma import get_property_collection
from app.models import sql_models

logger = logging.getLogger(__name__)

def sync_postgres_to_chroma(db: Session):
    """
    Scans Postgres for properties and ensures they are indexed in ChromaDB.
    Useful for data added via SQL or Admin seeds that bypassed the PDF ingestion pipeline.
    """
    collection = get_property_collection()

    # 1. Fetch all Properties
    properties = db.query(sql_models.Property).all()

    synced_count = 0
    errors = []

    for prop in properties:
        try:
            # We construct a rich text representation.
            text_representation = (
                f"Property Details:\n"
                f"State: {prop.state}\n"
                f"District: {prop.district}\n"
                f"Tehsil: {prop.tehsil}\n"
                f"Village: {prop.village}\n"
                f"Plot No: {prop.plot_no}\n"
                f"House No: {prop.house_no or 'N/A'}\n"
            )

            # Fetch related info to make search better
            transactions = (
                db.query(sql_models.Transaction).filter_by(property_id=prop.id).all()
            )
            if transactions:
                text_representation += "\nTransactions:\n"
                for txn in transactions:
                    text_representation += (
                        f"- Sold by {txn.seller.name} to {txn.buyer.name} "
                        f"on {txn.registration_date}\n"
                    )

            # Metadata for filtering
            metadata = {
                "property_id": prop.id,
                "district": prop.district,
                "village": prop.village,
                "plot_no": prop.plot_no,
                "sync_source": "postgres_sync_service",
            }

            # Generate a consistent ID based on property ID to avoid duplicates on re-runs
            chroma_id = f"summary_{prop.id}"

            collection.upsert(
                documents=[text_representation], metadatas=[metadata], ids=[chroma_id]
            )
            synced_count += 1

        except Exception as e:
            errors.append(f"Failed to sync Property ID {prop.id}: {str(e)}")

    return {"status": "completed", "synced_properties": synced_count, "errors": errors}

def sync_postgres_to_neo4j(db: Session):
    """
    Scans Postgres for properties and transactions and ensures they are seeded in Neo4j.
    Now with batching for high-performance handling of data.
    """
    from app.services.neo4j_service import get_driver, init_schema
    
    init_schema()
    driver = get_driver()
    if not driver:
        return {"status": "error", "message": "Could not connect to Neo4j"}

    properties = db.query(sql_models.Property).all()
    transactions = db.query(sql_models.Transaction).all()
    persons = db.query(sql_models.Person).all()
    documents = db.query(sql_models.Document).all()
    
    nodes_created = 0
    rels_created = 0
    BATCH_SIZE = 100
    
    with driver.session() as session:
        # 1. Sync Persons in Batches
        for i in range(0, len(persons), BATCH_SIZE):
            batch = persons[i : i + BATCH_SIZE]
            for p in batch:
                session.run(
                    "MERGE (n:Person {id: $id}) "
                    "SET n.name = $name, n.pan = $pan, n.aadhaar = $aadhaar",
                    id=p.id, name=p.name, pan=p.pan_number or "N/A", aadhaar=p.aadhaar_number or "N/A"
                )
            nodes_created += len(batch)
            
        # 2. Sync Properties in Batches
        for i in range(0, len(properties), BATCH_SIZE):
            batch = properties[i : i + BATCH_SIZE]
            for pr in batch:
                session.run(
                    "MERGE (n:Property {id: $id}) "
                    "SET n.state = $state, n.district = $district, n.village = $village, n.plot_no = $plot",
                    id=pr.id, state=pr.state, district=pr.district, village=pr.village, plot=pr.plot_no
                )
            nodes_created += len(batch)
            
        # 3. Sync Documents in Batches
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i : i + BATCH_SIZE]
            for doc in batch:
                session.run(
                    "MERGE (n:Document {id: $id}) "
                    "SET n.file_path = $path, n.file_hash = $hash",
                    id=doc.id, path=doc.file_path, hash=doc.file_hash
                )
            nodes_created += len(batch)

        # 4. Sync Transactions in Batches
        valid_txns = [t for t in transactions if t.seller_id and t.buyer_id and t.property_id]
        for i in range(0, len(valid_txns), BATCH_SIZE):
            batch = valid_txns[i : i + BATCH_SIZE]
            for t in batch:
                # Merge Transaction Node
                session.run(
                    "MERGE (trn:Transaction {id: $id}) "
                    "SET trn.date = $date, trn.document_id = $doc_id",
                    id=t.id, date=str(t.registration_date) if t.registration_date else "N/A", doc_id=t.document_id
                )
                
                # Create relationships by matching unique IDs
                session.run(
                    "MATCH (s:Person {id: $seller_id}) "
                    "MATCH (b:Person {id: $buyer_id}) "
                    "MATCH (p:Property {id: $prop_id}) "
                    "MATCH (t:Transaction {id: $t_id}) "
                    "MERGE (s)-[:SOLD]->(t) "
                    "MERGE (t)-[:BOUGHT_BY]->(b) "
                    "MERGE (t)-[:FOR_PROPERTY]->(p) "
                    "WITH t "
                    "MATCH (d:Document {id: $doc_id}) "
                    "WHERE $doc_id IS NOT NULL "
                    "MERGE (t)-[:BASED_ON]->(d)",
                    seller_id=t.seller_id, buyer_id=t.buyer_id, prop_id=t.property_id, t_id=t.id, doc_id=t.document_id
                )
            rels_created += (len(batch) * 4)  # ~4 rels per txn

        # 5. Identify and create Cross-Matches
        # If two different documents support transactions for the same property, they are cross-matched.
        session.run(
            "MATCH (d1:Document)<-[:BASED_ON]-(t1:Transaction)-[:FOR_PROPERTY]->(p:Property)<-[:FOR_PROPERTY]-(t2:Transaction)-[:BASED_ON]->(d2:Document) "
            "WHERE id(d1) < id(d2) AND d1.id <> d2.id "
            "MERGE (d1)-[r:CROSS_MATCH_WITH {property_id: p.id}]-(d2)"
        )


    return {"status": "completed", "nodes_created": nodes_created, "rels_created": rels_created}
