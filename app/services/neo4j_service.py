import logging
from neo4j import GraphDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

URI = settings.NEO4J_URI
USER = settings.NEO4J_USERNAME
PASS = settings.NEO4J_PASSWORD
AUTH = (USER, PASS)

_driver = None

def get_driver():
    global _driver
    if not _driver:
        try:
            _driver = GraphDatabase.driver(URI, auth=AUTH)
            # Verify connection
            _driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            _driver = None
    return _driver

def init_schema():
    """Create basic constraints to enforce data integrity in the graph."""
    d = get_driver()
    if not d:
        return
    try:
        with d.session() as session:
            # Person uniqueness by ID (much safer than name)
            session.run("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
            # Property uniqueness
            session.run("CREATE CONSTRAINT property_id IF NOT EXISTS FOR (pr:Property) REQUIRE pr.id IS UNIQUE")
            # Transaction uniqueness
            session.run("CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE")
        logger.info("Neo4j schema constraints initialized.")
    except Exception as e:
        logger.error(f"Error initializing Neo4j schema: {e}")

def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def get_ownership_chain(property_id: int) -> list:
    """Fetch the full chain of title for a property from Neo4j."""
    d = get_driver()
    if not d:
        return []
    try:
        with d.session() as session:
            result = session.run(
                "MATCH (s:Person)-[:SOLD]->(t:Transaction)-[:BOUGHT_BY]->(b:Person) "
                "MATCH (t)-[:FOR_PROPERTY]->(pr:Property) "
                "WHERE pr.id = $pid "
                "OPTIONAL MATCH (t)-[:BASED_ON]->(d:Document) "
                "RETURN s.name AS seller, s.id AS seller_id, s.pan AS seller_pan, s.aadhaar AS seller_aadhaar, "
                "b.name AS buyer, b.id AS buyer_id, b.pan AS buyer_pan, b.aadhaar AS buyer_aadhaar, "
                "t.date AS date, t.id AS txn_id, "
                "pr.id AS prop_id, pr.plot_no AS plot, pr.village AS village, pr.district AS district, "
                "d.id AS doc_id, d.file_path AS doc_path "
                "ORDER BY t.date ASC",
                pid=property_id,
            )
            return result.data()
    except Exception as e:
        logger.error(f"Neo4j ownership chain query failed: {e}")
        return []


def get_full_network(limit: int = 200) -> dict:
    """Fetch the full person-property-transaction network from Neo4j."""
    d = get_driver()
    if not d:
        return {"nodes": [], "edges": []}
    try:
        with d.session() as session:
            # Fetch all transactions with their connections
            result = session.run(
                "MATCH (s:Person)-[:SOLD]->(t:Transaction)-[:BOUGHT_BY]->(b:Person) "
                "MATCH (t)-[:FOR_PROPERTY]->(pr:Property) "
                "OPTIONAL MATCH (t)-[:BASED_ON]->(d:Document) "
                "RETURN s.name AS seller, s.id AS seller_id, s.pan AS seller_pan, s.aadhaar AS seller_aadhaar, "
                "b.name AS buyer, b.id AS buyer_id, b.pan AS buyer_pan, b.aadhaar AS buyer_aadhaar, "
                "t.id AS txn_id, t.date AS date, "
                "pr.id AS prop_id, pr.plot_no AS plot, pr.village AS village, "
                "d.id AS doc_id, d.file_path AS doc_path "
                "LIMIT $limit",
                limit=limit,
            )
            records = result.data()

            nodes_map = {}  # id -> node dict
            edges = []

            for rec in records:
                # Seller node
                s_key = f"person_{rec['seller_id']}"
                if s_key not in nodes_map:
                    nodes_map[s_key] = {
                        "id": s_key,
                        "label": rec["seller"] or "Unknown",
                        "type": "seller",
                        "pan": rec.get("seller_pan"),
                        "aadhaar": rec.get("seller_aadhaar"),
                    }
                # Buyer node
                b_key = f"person_{rec['buyer_id']}"
                if b_key not in nodes_map:
                    nodes_map[b_key] = {
                        "id": b_key,
                        "label": rec["buyer"] or "Unknown",
                        "type": "buyer",
                        "pan": rec.get("buyer_pan"),
                        "aadhaar": rec.get("buyer_aadhaar"),
                    }
                # Property node
                p_key = f"prop_{rec['prop_id']}"
                if p_key not in nodes_map:
                    nodes_map[p_key] = {
                        "id": p_key,
                        "label": f"Plot {rec['plot']}\n{rec['village']}",
                        "type": "property",
                    }
                # Transaction node
                t_key = f"txn_{rec['txn_id']}"
                if t_key not in nodes_map:
                    nodes_map[t_key] = {
                        "id": t_key,
                        "label": f"Txn\n{rec['date'] or ''}",
                        "type": "transaction",
                    }
                # Edges
                edges.append({"source": s_key, "target": t_key, "label": "SOLD"})
                edges.append({"source": t_key, "target": b_key, "label": "BOUGHT_BY"})
                edges.append({"source": t_key, "target": p_key, "label": "FOR_PROPERTY"})
                
                # Document node and edge (if present)
                if rec.get("doc_id") is not None:
                    d_key = f"doc_{rec['doc_id']}"
                    if d_key not in nodes_map:
                        filename = rec["doc_path"].split("/")[-1].split("\\")[-1] if rec.get("doc_path") else f"Doc {rec['doc_id']}"
                        nodes_map[d_key] = {
                            "id": d_key,
                            "label": filename,
                            "type": "document",
                        }
                    edges.append({"source": t_key, "target": d_key, "label": "BASED_ON"})

            # Fetch CROSS_MATCH edges
            cross_result = session.run(
                "MATCH (d1:Document)-[r:CROSS_MATCH_WITH]->(d2:Document) "
                "RETURN d1.id AS doc1_id, d2.id AS doc2_id, r.property_id AS property_id"
            )
            for c_rec in cross_result.data():
                d1_key = f"doc_{c_rec['doc1_id']}"
                d2_key = f"doc_{c_rec['doc2_id']}"
                # Only add if nodes exist in the current limited network
                if d1_key in nodes_map and d2_key in nodes_map:
                    edges.append({"source": d1_key, "target": d2_key, "label": "CROSS_MATCH_WITH"})

            return {"nodes": list(nodes_map.values()), "edges": edges}
    except Exception as e:
        logger.error(f"Neo4j full network query failed: {e}")
        return {"nodes": [], "edges": []}
