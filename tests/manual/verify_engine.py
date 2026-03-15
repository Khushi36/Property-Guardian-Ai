
import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services import query_service

def verify_engine():
    print("Verifying Query Service...")
    db = SessionLocal()
    try:
        # 1. Test Search
        query = "Who owns Plot 101?"
        print(f"Query: {query}")
        
        response = query_service.natural_language_search(query, db)
        
        # Check if we got an answer
        answer = response.get("answer")
        print("Answer:", answer)
        
        # Check if sources are present (even empty is fine if raw docs used)
        sources = response.get("sources")
        print(f"Structured Sources: {len(sources)}")
        
        # We can't easily check if raw docs were used without inspecting the full_context passed to LLM,
        # but if we got a good answer without structured sources (for the mock data), it means it worked.
        # Although verify_fix.py showed we *do* have structured data for Plot 101 (ingested).
        
        if "John Doe" in str(answer) or "Jane Smith" in str(answer):
             print("SUCCESS: Answer contains expected entities.")
        else:
             print("WARNING: Answer might not be perfect, check content.")

    except Exception as e:
        print(f"Engine Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_engine()
