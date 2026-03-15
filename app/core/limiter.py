from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Initialize limiter with Redis storage if REDIS_URL is provided, else fallback to memory
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL if hasattr(settings, "REDIS_URL") and settings.REDIS_URL else None
)
