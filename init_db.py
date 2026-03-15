import sys
import os

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import engine, Base
from app.models import sql_models

print("Starting database initialization...")
try:
    # Create all tables defined in sql_models using the configured DATABASE_URL
    Base.metadata.create_all(bind=engine)
    print(f"SUCCESS: Database tables created at {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured DB'}")
except Exception as e:
    print(f"ERROR: {e}")
