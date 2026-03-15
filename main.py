from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.core.database import engine, Base
from app.core.config import settings
from app.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn
import os

# Database Initialization
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Property Guardian AI",
    description="A premium AI-powered property fraud detection and analysis system.",
    version="1.0.0"
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
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint to verify system status."""
    return {
        "status": "active",
        "system": "Property Guardian AI",
        "components": ["API", "PostgreSQL", "ChromaDB"]
    }

if __name__ == "__main__":
    import uvicorn
    # Use reload=False to prevent multiprocessing spawn crashes on Windows 
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
