from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request, Query
import logging
from collections import defaultdict
import time

logger = logging.getLogger(__name__)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import timedelta
from app.core import database
from app.core.database import get_db
from app.services import ingestion, query_service, fraud_detection, sync_service
from app.models import schemas, sql_models
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

# --- Auth Dependencies ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except security.JWTError:
        raise credentials_exception
        
    user = db.query(sql_models.User).filter(func.lower(sql_models.User.email) == token_data.email.lower()).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: sql_models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# --- Standard Auth Endpoints ---

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(sql_models.User).filter(func.lower(sql_models.User.email) == form_data.username.lower()).first()
    if not user:
        # Avoid timing attacks by simulating verify? No, keep simple for now.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not security.verify_password(form_data.password, user.hashed_password):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    email_lower = user.email.lower()
    db_user = db.query(sql_models.User).filter(func.lower(sql_models.User.email) == email_lower).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(user.password)
    db_user = sql_models.User(email=email_lower, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Password Reset Endpoints ---


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
def confirm_password_reset(request: Request, data: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    email_lower = data.email.lower()
    user = db.query(sql_models.User).filter(func.lower(sql_models.User.email) == email_lower).first()
    if not user:
        # Avoid disclosure: return success even if user not found (or generic error)
        return {"message": "If an account exists, the password has been reset."}
        
    # Reset password directly (Simplified flow as requested)
    user.hashed_password = security.get_password_hash(data.new_password)
    db.commit()
    
    return {"message": "Password reset successfully. You can now log in."}

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: sql_models.User = Depends(get_current_active_user)):
    return current_user

# --- Google OAuth2 Endpoints (Placeholder) ---
# To fully implement, we need GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
@router.get("/login/google")
async def login_google():
    return {
        "url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8000/api/v1/auth/google/callback&scope=openid%20email%20profile"
    }

@router.get("/auth/google/callback")
async def auth_google_callback(code: str, db: Session = Depends(get_db)):
    # 1. Exchange code for token (requires client secret)
    # 2. Get user info from Google
    # 3. Create or get user in DB
    # 4. Create JWT token
    # 5. Redirect to Streamlit with token in query param? Or show token?
    # For now, we return a mock success
    return {"message": "Google Login Callback received. Configure Client ID/Secret to activate."}

# --- Application Endpoints (Secured) ---

@router.post("/ingest", response_model=schemas.IngestionResponse)
def ingest_document(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: sql_models.User = Depends(get_current_active_user)
):
    logger.info(f"Ingestion: received {len(files)} files")
    results = []
    errors = []
    
    for file in files:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            errors.append(f"{file.filename}: Not a PDF file. Only PDF files are accepted.")
            continue
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
            errors.append(f"{file.filename}: File too large (max 50MB).")
            continue
        res = ingestion.process_document(file=file, db=db)
        if res.get("status") == "error":
            errors.append(f"{file.filename}: {res['message']}")
        elif res.get("status") == "skipped":
            results.append(f"{file.filename} (Skipped: {res['message']})")
        else:
            p_no = res.get('extracted_data', {}).get('plot_no', 'unknown')
            results.append(f"{file.filename} (Plot: {p_no})")
    
    if not results and errors:
        raise HTTPException(status_code=400, detail=f"Failed to process files: {'; '.join(errors)}")
        
    return schemas.IngestionResponse(
        document_id=0, 
        file_hash="bulk",
        message=f"Processed {len(results)}/{len(files)} files. Success: {', '.join(results)}. Errors: {', '.join(errors)}"
    )

# --- Rate Limiting built entirely on slowapi ---

@router.get("/query/natural_language")
@limiter.limit("10/minute")
def query_natural_language(request: Request, q: str, session_id: Optional[str] = None, db: Session = Depends(get_db), current_user: sql_models.User = Depends(get_current_active_user)):
    return query_service.natural_language_search(q, db, session_id)

@router.get("/query/ai_sql")
@limiter.limit("10/minute")
def query_ai_sql(request: Request, q: str, db: Session = Depends(get_db), current_user: sql_models.User = Depends(get_current_active_user)):
    try:
        return query_service.ai_to_sql_query(q, db)
    except Exception as e:
        logger.error(f"AI SQL Execution Error: {e}")
        return {"error": "Failed to execute search query"}

# RE-ENABLED: /query/direct_sql endpoint with strict security (SELECT only)
@router.post("/query/direct_sql")
def query_direct_sql(
    request: schemas.SQLRequest, 
    db_readonly: Session = Depends(database.get_readonly_db), 
    db_write: Session = Depends(get_db),
    current_user: sql_models.User = Depends(get_current_active_user)
):
    """Execute a read-only SQL query against the property database."""
    query_upper = request.query.strip().upper()
    
    # Basic protection against destructive commands
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
    for cmd in forbidden:
        if cmd in query_upper:
            raise HTTPException(status_code=400, detail=f"Operation '{cmd}' is NOT allowed. Only SELECT queries are permitted.")
            
    if not query_upper.startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed for security reasons.")
    
    # Use write-able DB for audit logging, readonly DB for the query itself
    return query_service.execute_direct_sql_safe(request.query, db_readonly, user_id=current_user.id, log_db=db_write)

@router.get("/fraud-check")
def check_fraud(db: Session = Depends(get_db), current_user: sql_models.User = Depends(get_current_active_user)):
    return fraud_detection.detect_fraud(db)

@router.get("/properties")
def list_properties(
    db: Session = Depends(get_db),
    current_user: sql_models.User = Depends(get_current_active_user),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List all properties in the database with pagination."""
    total = db.query(sql_models.Property).count()
    props = db.query(sql_models.Property).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": p.id,
                "state": p.state,
                "district": p.district,
                "tehsil": p.tehsil,
                "village": p.village,
                "plot_no": p.plot_no,
                "house_no": p.house_no,
                "transaction_count": len(p.transactions) if p.transactions else 0
            }
            for p in props
        ]
    }

@router.get("/transactions")
def list_transactions(
    db: Session = Depends(get_db),
    current_user: sql_models.User = Depends(get_current_active_user),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List all transactions with seller/buyer details, paginated."""
    total = db.query(sql_models.Transaction).count()
    txns = db.query(sql_models.Transaction).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": t.id,
                "property": f"{t.property.village}, Plot {t.property.plot_no}" if t.property else "Unknown",
                "seller": t.seller.name if t.seller else "Unknown",
                "buyer": t.buyer.name if t.buyer else "Unknown",
                "date": t.registration_date.isoformat() if t.registration_date else "Unknown",
                "document_id": t.document_id
            }
            for t in txns
        ]
    }

@router.post("/system/sync")
def sync_data(db: Session = Depends(get_db), current_user: sql_models.User = Depends(get_current_active_user)):
    return sync_service.sync_postgres_to_chroma(db)
