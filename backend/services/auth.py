"""Authentication service functions"""
import os
import uuid
import bcrypt
import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import User

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=int(os.environ.get('BCRYPT_ROUNDS', 12)))
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


async def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> User:
    """Get current authenticated user from cookie or header"""
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

    # Try cookie first
    session_token = request.cookies.get('session_token')

    # Fallback to Authorization header
    if not session_token and authorization:
        if authorization.startswith('Bearer '):
            session_token = authorization.replace('Bearer ', '')

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Find session
    session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    # Get user
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    # Convert datetime
    if isinstance(user_doc['created_at'], str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])

    return User(**user_doc)


async def create_session(user_id: str) -> str:
    """Create a new session for user"""
    session_token = f"session_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return session_token


async def seed_admin():
    """Seed admin account if not exists"""
    admin_email = "info@kaimeralearning.com"
    existing = await db.users.find_one({"email": admin_email}, {"_id": 0})

    if not existing:
        admin_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash_val = hash_password("solidarity&peace2023")

        await db.users.insert_one({
            "user_id": admin_id,
            "email": admin_email,
            "name": "Kaimera Admin",
            "role": "admin",
            "credits": 0.0,
            "picture": None,
            "password_hash": password_hash_val,
            "is_approved": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"Admin account seeded: {admin_email}")
