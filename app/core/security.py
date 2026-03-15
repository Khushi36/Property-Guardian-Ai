from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import jwt, JWTError
import bcrypt # Using direct bcrypt instead of passlib for stability
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt.checkpw requires bytes
    h_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    p_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        
    return bcrypt.checkpw(p_bytes, h_bytes)

def get_password_hash(password: str) -> str:
    p_bytes = password.encode('utf-8') if isinstance(password, str) else password
    # gensalt() generates a salt, hashpw hashes it
    return bcrypt.hashpw(p_bytes, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
