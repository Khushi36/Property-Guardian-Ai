import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, ForeignKey,
                        Integer, String, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
    tehsil = Column(String, nullable=False)
    village = Column(String, nullable=False)
    plot_no = Column(String, nullable=False)
    house_no = Column(String, nullable=True)  # House No might be optional for land

    # Relationships
    transactions = relationship("Transaction", back_populates="property")

    # Unique constraint to identify physical property
    __table_args__ = (
        UniqueConstraint(
            "state",
            "district",
            "tehsil",
            "village",
            "plot_no",
            "house_no",
            name="uix_property_location",
        ),
    )

    def __repr__(self):
        return f"<Property(id={self.id}, plot={self.plot_no}, village={self.village})>"


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    pan_number = Column(
        String, unique=True, nullable=True
    )  # Assuming PAN as a unique identifier for simplicity
    aadhaar_number = Column(String, unique=True, nullable=True)  # Or Aadhaar
    role = Column(
        String
    )  # 'seller', 'buyer', or 'official' - though roles change per transaction

    # A person can be involved in many transactions as buyer or seller
    # We might not strictly need back_populates here if we don't access specific lists often

    def __repr__(self):
        return f"<Person(id={self.id}, name={self.name})>"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    file_hash = Column(
        String, unique=True, nullable=False
    )  # SHA256 hash to detect duplicate files
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Metadata extracted from OCR could also be stored here for convenience,
    # but the prompt asks for it in Chroma. We'll keep it minimal here.

    transactions = relationship("Transaction", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, hash={self.file_hash})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    registration_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())

    # Relationships
    property = relationship("Property", back_populates="transactions")
    seller = relationship("Person", foreign_keys=[seller_id])
    buyer = relationship("Person", foreign_keys=[buyer_id])
    document = relationship("Document", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, property_id={self.property_id}, date={self.registration_date})>"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(String, nullable=False)
    reasoning_details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # 'admin', 'user'

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class AuditLog(Base):
    __tablename__ = "sql_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
