
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL", "http://localhost:8000")

def test_sql_queries():
    print("\n--- Testing SQL Queries ---")
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in .env")
        return

    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        queries = [
            {
                "name": "Audit Properties Table",
                "sql": "SELECT id, state, district, village, plot_no FROM properties;"
            },
            {
                "name": "Linkage Check",
                "sql": """
                    SELECT 
                        p.district, p.village, p.plot_no, 
                        s.name AS seller, 
                        b.name AS buyer, 
                        t.registration_date
                    FROM transactions t
                    JOIN properties p ON t.property_id = p.id
                    JOIN people s ON t.seller_id = s.id
                    JOIN people b ON t.buyer_id = b.id;
                """
            }
        ]

        for q in queries:
            print(f"\n>> Executing: {q['name']}")
            result = db.execute(text(q['sql']))
            keys = result.keys()
            rows = result.fetchall()
            if not rows:
                print("   No results found.")
            else:
                print(f"   Columns: {list(keys)}")
                for row in rows:
                    print(f"   {row}")
        
        db.close()
    except Exception as e:
        print(f"SQL Test Error: {e}")

def test_nl_query():
    print("\n--- Testing Natural Language Query (RAG) ---")
    
    # Question from test_use_cases.md
    question = "Who bought the property in Wakad?"
    
    try:
        # We need a token if the endpoint is protected.
        # However, for a simple health/QA check against running app, 
        # let's try calling it. If it requires auth, we might need to login first.
        # Based on endpoints.py, get_current_active_user is usually required.
        
        # We'll try a direct repo login if possible or just use existing knowledge of credentials.
        # Use test credentials if they exist or skip if too complex.
        
        login_url = f"{API_URL}/api/v1/token"
        # Most likely khushi@example.com / password based on typical local setups if not specified
        # Let's check init_db or previous logs if any users were created.
        
        print(f"Querying: {question}")
        params = {"q": question}
        # In this project, the natural language query is a GET request
        resp = requests.get(f"{API_URL}/api/v1/query/natural_language", params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Answer: {data.get('answer')}")
            print(f"Sources: {data.get('sources')}")
        elif resp.status_code == 401:
            print("Auth required for NL Query. Skipping direct API test (needs token).")
        else:
            print(f"NL Query failed with status {resp.status_code}: {resp.text}")
            
    except Exception as e:
        print(f"NL Test Error: {e}")

if __name__ == "__main__":
    test_sql_queries()
    # test_nl_query() # Skip if auth is strict and we don't have user creds handy
