from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class PropertyCreate(BaseModel):
    state: str
    district: str
    tehsil: str
    village: str
    plot_no: str
    house_no: Optional[str] = None


class PropertyResponse(PropertyCreate):
    id: int

    class Config:
        from_attributes = True


class PersonCreate(BaseModel):
    name: str
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None


class PersonResponse(PersonCreate):
    id: int

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    property_id: int
    seller_id: int
    buyer_id: int
    registration_date: Optional[date] = None


class IngestionResponse(BaseModel):
    document_id: int
    file_hash: str
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    role: str

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    email: str
    new_password: str


class SQLRequest(BaseModel):
    query: str


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    query_text: str
    timestamp: datetime

    class Config:
        from_attributes = True
