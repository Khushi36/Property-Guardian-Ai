import time
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.endpoints import router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

# Database Initialization
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Property Guardian AI",
    description="A premium AI-powered property fraud detection and analysis system.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
origins = []
if settings.ALLOWED_ORIGINS:
    import json

    origins = json.loads(settings.ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def read_root():
    """Serve a minimal API status."""
    return {
        "message": "Property Guardian AI API is running.",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify real system status of all components."""
    status_map = {
        "API": "active",
        "PostgreSQL": "inactive",
        "ChromaDB": "inactive",
        "Neo4j": "inactive"
    }
    
    # 1. Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        status_map["PostgreSQL"] = "active"
    except Exception as e:
        logger.error(f"Health Check - PostgreSQL Failure: {e}")

    # 2. Check ChromaDB
    try:
        from app.core.chroma import get_chroma_client
        chroma_client = get_chroma_client()
        chroma_client.heartbeat()
        status_map["ChromaDB"] = "active"
    except Exception as e:
        logger.error(f"Health Check - ChromaDB Failure: {e}")

    # 3. Check Neo4j
    try:
        from app.services.neo4j_service import get_driver
        driver = get_driver()
        if driver:
            driver.verify_connectivity()
            status_map["Neo4j"] = "active"
    except Exception as e:
        logger.error(f"Health Check - Neo4j Failure: {e}")

    overall_status = "active" if all(v == "active" for v in status_map.values()) else "degraded"
    
    return {
        "status": overall_status,
        "system": "Property Guardian AI",
        "components": status_map,
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn  # noqa: local import for direct-run only

    # Use reload=False to prevent multiprocessing spawn crashes on Windows
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
