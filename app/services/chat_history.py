import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import sql_models


def get_or_create_session(db: Session, session_id: Optional[str] = None):
    if not session_id:
        session_id = str(uuid.uuid4())

    session = db.query(sql_models.ChatSession).filter_by(id=session_id).first()
    if not session:
        session = sql_models.ChatSession(id=session_id)
        db.add(session)
        db.commit()
        db.refresh(session)

    return session


def add_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    reasoning_details: Optional[dict] = None,
):
    msg = sql_models.ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        reasoning_details=reasoning_details,
    )
    try:
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Failed to save chat message: {e}")


def get_history(db: Session, session_id: str, limit: int = 10):
    """
    Returns history as a list of dicts: [{"role": "user", "content": "..."}]
    """
    session = get_or_create_session(db, session_id)
    # Fetch last N messages
    msgs = (
        db.query(sql_models.ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(sql_models.ChatMessage.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Reverse to get chronological order
    history = [
        {"role": m.role, "content": m.content, "reasoning_details": m.reasoning_details}
        for m in reversed(msgs)
    ]
    return history
