from app.services.neo4j_service import get_driver, init_schema
import logging

logging.basicConfig(level=logging.INFO)

def wipe_and_init():
    driver = get_driver()
    if not driver:
        print("Could not connect to Neo4j.")
        return
    
    with driver.session() as session:
        print("Wiping all nodes and relationships...")
        session.run("MATCH (n) DETACH DELETE n")
        
        print("Dropping old constraints (if any)...")
        # In Neo4j 4.x/5.x, renaming constraints can be tricky, but we can try to drop person_name if it exists
        try:
            session.run("DROP CONSTRAINT person_name IF EXISTS")
        except Exception as e:
            print(f"Note: Could not drop person_name constraint: {e}")

    print("Re-initializing schema with new constraints...")
    init_schema()
    print("Done!")

if __name__ == "__main__":
    wipe_and_init()
