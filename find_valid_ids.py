import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def find_ids():
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        print("--- Properties with Transactions ---")
        query = text("""
            SELECT p.id, p.plot_no, p.village, COUNT(t.id) as txns
            FROM properties p
            JOIN transactions t ON p.id = t.property_id
            GROUP BY p.id, p.plot_no, p.village
            ORDER BY txns DESC
            LIMIT 20
        """)
        res = conn.execute(query)
        for r in res:
            print(f"ID: {r[0]}, Plot: {r[1]}, Village: {r[2]}, Txns: {r[3]}")

if __name__ == "__main__":
    find_ids()
