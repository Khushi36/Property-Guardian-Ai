import platform as _platform
# Monkey-patch the hanging WMI call before any other imports
_platform._wmi_query = lambda *a, **kw: (_ for _ in ()).throw(OSError("patched"))
_platform.version = lambda: "Windows"

import os
import sys
import requests
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QA-Verify")

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL", "http://localhost:8000")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password123")


def test_sql_queries():
    print("\n--- 🗄️ Testing SQL Queries (PostgreSQL) ---")
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL not found in .env")
        return False

    try:
        # Use a short timeout for connection (5 seconds)
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        queries = [
            {
                "name": "Audit Properties Table",
                "sql": "SELECT id, state, district, village, plot_no FROM properties LIMIT 5;",
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
                    JOIN people b ON t.buyer_id = b.id
                    LIMIT 5;
                """,
            },
        ]

        success = True
        for q in queries:
            print(f"\n>> Executing: {q['name']}")
            try:
                result = db.execute(text(q["sql"]))
                keys = result.keys()
                rows = result.fetchall()
                if not rows:
                    print("   ⚠️ No results found (Database might be empty).")
                else:
                    print(f"   ✅ Columns: {list(keys)}")
                    for row in rows:
                        print(f"   {row}")
            except Exception as qe:
                print(f"   ❌ Query Error: {qe}")
                success = False

        db.close()
        return success
    except Exception as e:
        print(f"❌ SQL Connection Error: {e}")
        return False


def test_neo4j_connectivity():
    print("\n--- 🕸️ Testing Neo4j Connectivity ---")
    try:
        from neo4j import GraphDatabase
        # Add connection timeout of 5 seconds to Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS), connection_timeout=5.0, max_connection_lifetime=5.0)
        
        # Use a session with a short acquisition timeout
        with driver.session(connection_acquisition_timeout=5.0) as session:
            # Check node counts
            result = session.run("MATCH (n) RETURN labels(n) as label, count(n) as count")
            counts = result.data()
            if not counts:
                print("   ⚠️ Neo4j is connected but has no nodes.")
            else:
                print("   ✅ Graph Summary:")
                for c in counts:
                    print(f"      - {c['label']}: {c['count']}")
        
        driver.close()
        return True
    except ImportError:
        print("   ❌ Error: 'neo4j' package not installed. Run 'pip install neo4j'.")
        return False
    except Exception as e:
        print(f"   ❌ Neo4j Connection Error: {e}")
        return False


def test_api_health():
    print("\n--- 🚀 Testing API Health ---")
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ API Status: {data.get('status')}")
            print(f"   ✅ Components: {data.get('components')}")
            return True
        else:
            print(f"   ❌ API Health check failed with status {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ API Connection Error: {e}")
        return False


def test_nl_query():
    print("\n--- 🧠 Testing Natural Language Query (RAG) ---")
    question = "Who bought the property in Wakad?"

    try:
        print(f"   Querying: \"{question}\"")
        params = {"q": question}
        # Attempt a request - might fail if auth is required but a good test of endpoint existence
        resp = requests.get(f"{API_URL}/api/v1/query/natural_language", params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Answer received: {data.get('answer')[:100]}...")
            return True
        elif resp.status_code == 401:
            print("   🔒 Auth Required (401). Endpoint is protected as expected.")
            return True # Consider this a success in terms of endpoint existence
        else:
            print(f"   ❌ NL Query failed with status {resp.status_code}: {resp.text}")
            return False

    except Exception as e:
        print(f"   ❌ NL Test Connection Error: {e}")
        return False


if __name__ == "__main__":
    sql_ok = test_sql_queries()
    neo_ok = test_neo4j_connectivity()
    api_ok = test_api_health()
    # nl_ok = test_nl_query() # Optional

    print("\n" + "="*30)
    print("      FINAL QA STATUS")
    print("="*30)
    print(f"PostgreSQL: {'✅ PASS' if sql_ok else '❌ FAIL'}")
    print(f"Neo4j:      {'✅ PASS' if neo_ok else '❌ FAIL'}")
    print(f"FastAPI:    {'✅ PASS' if api_ok else '❌ FAIL'}")
    print("="*30)

    if not (sql_ok and neo_ok and api_ok):
        sys.exit(1)
    sys.exit(0)
