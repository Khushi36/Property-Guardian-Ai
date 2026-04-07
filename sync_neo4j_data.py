from app.core.database import SessionLocal
from app.services.sync_service import sync_postgres_to_neo4j
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
try:
    print("Starting Neo4j Sync...")
    res = sync_postgres_to_neo4j(db)
    print("Sync Result:", res)
finally:
    db.close()
