import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def check_neo4j():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            print("--- Neo4j Node Counts ---")
            res = session.run("MATCH (n) RETURN labels(n) as label, count(n) as count")
            for r in res:
                print(f"Label: {r['label']}, Count: {r['count']}")
            
            print("\n--- Sample Property Nodes ---")
            res = session.run("MATCH (p:Property) RETURN p.id as id, p.plot_no as plot LIMIT 5")
            for r in res:
                print(f"Property ID: {r['id']}, Plot: {r['plot']}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_neo4j()
