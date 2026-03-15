from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, select, literal, case, and_
from app.models import sql_models

def detect_fraud(db: Session):
    """
    Detects fraud using Chain of Title verification via optimized SQL Window Functions.
    
    Logic:
    1. Sort transactions for each property by date.
    2. Compare current Seller with Previous Buyer.
    3. If they don't match, it's a broken chain.
    
    Performance: O(1) query complexity for the app server (O(N) in DB, but indexed).
    """
    
    # Aliases for clarity
    t1 = aliased(sql_models.Transaction)
    
    # Step 1: Subquery with Window Function to get previous buyer
    # We select relevant columns and calculate 'prev_buyer_id'
    subquery = (
        select(
            t1.id,
            t1.property_id,
            t1.seller_id,
            t1.buyer_id,
            t1.registration_date,
            func.lag(t1.buyer_id).over(
                partition_by=t1.property_id,
                order_by=(t1.registration_date, t1.id)
            ).label('prev_buyer_id')
        )
    ).subquery()
    
    # Step 2: Main Query to find discrepancies
    # Condition: 
    # 1. prev_buyer_id IS NOT NULL (it has a history)
    # 2. seller_id != prev_buyer_id (The person selling is not the last person who bought it)
    # We must also handle if prev_buyer_id is NULL, which means it's the first transaction. We don't flag first transactions as fraud.
    stmt = (
        select(
            subquery.c.property_id,
            subquery.c.registration_date,
            sql_models.Property.village,
            sql_models.Property.plot_no,
            sql_models.Person.name.label("seller_name"), # Current Seller
            # We need to join Person again for previous buyer (omitted for speed, can add if needed)
        )
        .join(sql_models.Property, subquery.c.property_id == sql_models.Property.id)
        .join(sql_models.Person, subquery.c.seller_id == sql_models.Person.id)
        .where(
            and_(
                subquery.c.prev_buyer_id.isnot(None), 
                subquery.c.seller_id != subquery.c.prev_buyer_id,
                # Add an exception or note for inheritance if we had a relationship flag, 
                # but since we don't, we will return these as "Verify required" instead of strict Fraud.
            )
        )
    )
    
    results = db.execute(stmt).all()
    
    fraud_report = []
    
    # Step 3: Format results
    for row in results:
        fraud_report.append({
            "property_id": row.property_id,
            "location": f"{row.village}, Plot {row.plot_no}",
            "risk_level": "HIGH",
            "reason": f"BROKEN CHAIN OF TITLE: The seller '{row.seller_name}' is NOT the last registered buyer of this property. Verification required.",
            "details": {
                "seller": row.seller_name,
                "date": row.registration_date.isoformat() if row.registration_date else "Unknown"
            }
        })
    
    # Step 4: Logic for "Double Selling" (Same Seller + Same Property across multiple transactions)
    # We look for any property where a person has acted as the seller more than once.
    # While some split-plot scenarios exist, in a simple model, selling the same plot twice is a major red flag.
    double_sell_stmt = (
        select(
            sql_models.Transaction.property_id,
            sql_models.Transaction.seller_id,
            func.count(sql_models.Transaction.id).label("sale_count"),
            sql_models.Property.village,
            sql_models.Property.plot_no,
            sql_models.Person.name.label("seller_name"),
            sql_models.Person.aadhaar_number,
            sql_models.Person.pan_number
        )
        .join(sql_models.Property, sql_models.Transaction.property_id == sql_models.Property.id)
        .join(sql_models.Person, sql_models.Transaction.seller_id == sql_models.Person.id)
        .group_by(
            sql_models.Transaction.property_id, 
            sql_models.Transaction.seller_id,
            sql_models.Property.village,
            sql_models.Property.plot_no,
            sql_models.Person.name,
            sql_models.Person.aadhaar_number,
            sql_models.Person.pan_number
        )
        .having(func.count(sql_models.Transaction.id) > 1)
    )
    
    double_sell_results = db.execute(double_sell_stmt).all()
    
    for row in double_sell_results:
        fraud_report.append({
            "property_id": row.property_id,
            "location": f"{row.village}, Plot {row.plot_no}",
            "risk_level": "CRITICAL", # High priority
            "reason": f"DOUBLE SELLING DETECTED. The seller '{row.seller_name}' (ID/Aadhaar: {row.aadhaar_number or row.pan_number or 'Unknown'}) has sold this same property {row.sale_count} times. This is a severe fraud indicator.",
            "details": {
                "seller": row.seller_name,
                "identity": row.aadhaar_number or row.pan_number,
                "sale_count": row.sale_count
            }
        })
            
    return fraud_report

