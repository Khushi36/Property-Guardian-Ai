
import sys
import os

# Ensure app can be imported
sys.path.append(os.getcwd())

from app.core.chroma import get_property_collection

def verify_search():
    print("Getting collection...")
    try:
        collection = get_property_collection()
        print(f"Collection count: {collection.count()}")
        
        query = "Plot 101"
        print(f"Querying for '{query}'...")
        
        results = collection.query(
            query_texts=[query],
            n_results=1
        )
        
        if results['documents'] and results['documents'][0]:
            print("SUCCESS: Found results.")
            print(f"Content: {results['documents'][0][0][:100]}...")
            print(f"Metadata: {results['metadatas'][0][0]}")
        else:
            print("FAILURE: No results found.")
            
    except Exception as e:
        print(f"Search Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_search()
