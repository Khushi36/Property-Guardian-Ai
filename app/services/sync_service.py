import uuid

from sqlalchemy.orm import Session

from app.core.chroma import get_property_collection
from app.models import sql_models


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
            # Check if this property is already in Chroma?
            # Chroma doesn't support complex "exists" checks easily without query.
            # But we can regenerate the ID or just search by metadata.
            # Strategy: We will UPSERT. If it exists, it updates.

            # We need a text representation.
            # If there are documents, we use their text?
            # But what if this is a "Metadata Only" property?
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
