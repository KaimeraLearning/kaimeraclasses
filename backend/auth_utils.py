"""Authentication utilities shared across routes"""
import os
from fastapi import HTTPException, Request
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

# Re-export db
from database import db


class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    credits: float = 0.0
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_approved: bool = True
    phone: Optional[str] = None
    bio: Optional[str] = None
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    created_at: datetime


async def get_current_user(request: Request, authorization: Optional[str] = None) -> User:
    """Get the current authenticated user from session cookie or Authorization header"""
    session_token = None

    # Check cookie first
    session_token = request.cookies.get("session_token")

    # Then check Authorization header
    if not session_token and authorization:
        if authorization.startswith("Bearer "):
            session_token = authorization[7:]
        else:
            session_token = authorization

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Look up session
    session = await db.sessions.find_one({"session_id": session_token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check expiry
    expires_at = session.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            await db.sessions.delete_one({"session_id": session_token})
            raise HTTPException(status_code=401, detail="Session expired")

    # Get user
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])

    return User(**user_doc)
