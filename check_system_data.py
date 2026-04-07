import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

load_dotenv()

def check_db():
    print("--- Checking SQL Database ---")
    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        with engine.connect() as conn:
            # Check Properties
            res = conn.execute(text("SELECT id FROM properties WHERE id IN (14, 15, 18, 19, 20, 21, 23, 24, 25, 26, 27)"))
            ids = [r[0] for r in res]
            print(f"Found Property IDs: {ids}")
            
            # Check राजेश कुमार (Rajesh Kumar)
            res = conn.execute(text("SELECT name FROM people WHERE name ILIKE '%Rajesh Kumar%'"))
            names = [r[0] for r in res]
            print(f"Found People: {names}")
    except Exception as e:
        print(f"SQL Error: {e}")

def check_chroma():
    print("\n--- Checking ChromaDB ---")
    try:
        # Assuming default path or from env
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_collection("property_documents")
        
        # Check for property_id 26
        results = collection.get(where={"property_id": 26}, limit=1)
        if results and results.get("ids"):
            print(f"Found document for Property ID 26 in ChromaDB")
        else:
            print(f"Property ID 26 NOT found in ChromaDB")
            
        print(f"Total documents in collection: {collection.count()}")
    except Exception as e:
        print(f"ChromaDB Error: {e}")

if __name__ == "__main__":
    check_db()
    check_chroma()
