"""Auth routes"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Response, Header
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import db
from models.schemas import User, UserRegister, UserLogin
from services.auth import hash_password, verify_password, get_current_user, create_session
from services.helpers import generate_student_code, send_email, generate_otp

router = APIRouter()

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')


def validate_gmail(email: str):
    """Enforce @gmail.com only for manual user creation"""
    if not email.lower().endswith('@gmail.com'):
        raise HTTPException(status_code=400, detail="Only @gmail.com email addresses are allowed")


@router.post("/auth/register")
async def register(user_data: UserRegister):
    """Register new student - requires OTP verification first"""
    validate_gmail(user_data.email)

    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user_data.role != "student":
        raise HTTPException(status_code=403, detail="Only students can self-register. Teachers are created by admin.")

    if user_data.phone and user_data.phone.strip():
        phone_exists = await db.users.find_one({"phone": user_data.phone.strip()}, {"_id": 0, "email": 1})
        if phone_exists:
            raise HTTPException(status_code=400, detail="Phone number already registered with another account")

    # Check OTP verification
    otp_record = await db.otp_codes.find_one(
        {"email": user_data.email, "verified": True}, {"_id": 0}
    )
    if not otp_record:
        raise HTTPException(status_code=400, detail="Please verify your email with OTP first")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash_val = hash_password(user_data.password)
    student_code = await generate_student_code()

    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": "student",
        "credits": 0.0,
        "picture": None,
        "password_hash": password_hash_val,
        "is_approved": True,
        "is_verified": True,  # Self-registered with OTP = verified
        "phone": user_data.phone,
        "bio": None,
        "institute": user_data.institute,
        "goal": user_data.goal,
        "preferred_time_slot": user_data.preferred_time_slot,
        "student_code": student_code,
        "state": user_data.state,
        "city": user_data.city,
        "country": user_data.country,
        "grade": user_data.grade,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.users.insert_one(user_doc)
    await db.otp_codes.delete_many({"email": user_data.email})

    session_token = await create_session(user_id)
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)

    return {
        "user": user.model_dump(),
        "session_token": session_token,
        "message": f"Student account created! Your ID: {student_code}"
    }


@router.post("/auth/send-otp")
async def send_otp(request: Request):
    """Send OTP to email for self-signup verification"""
    body = await request.json()
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    validate_gmail(email)

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp = await generate_otp(email)

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #f8fafc; border-radius: 16px;">
        <h2 style="color: #0ea5e9; margin-bottom: 16px;">Kaimera Learning - Email Verification</h2>
        <p style="color: #475569; font-size: 16px; margin-bottom: 24px;">Your verification code is:</p>
        <div style="background: white; border: 2px solid #e2e8f0; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0f172a;">{otp}</span>
        </div>
        <p style="color: #94a3b8; font-size: 14px;">This code expires in 10 minutes. Do not share it with anyone.</p>
    </div>
    """

    await send_email(email, "Kaimera Learning - Verify Your Email", html_content)

    return {"message": "OTP sent to your email. Please check your inbox."}


@router.post("/auth/verify-otp")
async def verify_otp(request: Request):
    """Verify OTP code sent to email"""
    body = await request.json()
    email = body.get("email", "").strip().lower()
    otp = body.get("otp", "").strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP required")

    failed_count = await db.otp_codes.count_documents({"email": email, "failed_attempts": {"$gte": 5}})
    if failed_count > 0:
        await db.otp_codes.delete_many({"email": email})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please request a new OTP.")

    record = await db.otp_codes.find_one({"email": email, "otp": otp}, {"_id": 0})
    if not record:
        await db.otp_codes.update_one({"email": email}, {"$inc": {"failed_attempts": 1}})
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        await db.otp_codes.delete_many({"email": email})
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    await db.otp_codes.update_one({"email": email, "otp": otp}, {"$set": {"verified": True}})

    return {"message": "Email verified successfully!", "verified": True}


@router.post("/auth/login")
async def login(credentials: UserLogin, response: Response):
    """Login with email/password"""
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user_doc.get('password_hash'):
        raise HTTPException(status_code=401, detail="This account uses Google login")

    if not verify_password(credentials.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user_doc.get('is_blocked'):
        raise HTTPException(status_code=403, detail="Your account has been blocked by the administrator. Please contact support.")

    # Check if account is verified (manually created users need OTP verification)
    if not user_doc.get('is_verified', True):
        return {
            "needs_verification": True,
            "email": credentials.email,
            "message": "Account not verified. Please check your email for verification OTP."
        }

    session_token = await create_session(user_doc['user_id'])

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )

    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)

    return {"user": user.model_dump(), "session_token": session_token}


@router.post("/auth/verify-account")
async def verify_account(request: Request, response: Response):
    """Verify OTP for manually created accounts, then activate and login"""
    body = await request.json()
    email = body.get("email", "").strip().lower()
    otp = body.get("otp", "").strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP required")

    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Account not found")

    if user_doc.get('is_verified', True):
        raise HTTPException(status_code=400, detail="Account already verified")

    # Check OTP
    failed_count = await db.otp_codes.count_documents({"email": email, "failed_attempts": {"$gte": 5}})
    if failed_count > 0:
        await db.otp_codes.delete_many({"email": email})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please request a new OTP.")

    record = await db.otp_codes.find_one({"email": email, "otp": otp}, {"_id": 0})
    if not record:
        await db.otp_codes.update_one({"email": email}, {"$inc": {"failed_attempts": 1}})
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        await db.otp_codes.delete_many({"email": email})
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    # Mark user as verified
    await db.users.update_one({"email": email}, {"$set": {"is_verified": True}})
    await db.otp_codes.delete_many({"email": email})

    # Auto-login
    session_token = await create_session(user_doc['user_id'])

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )

    user_doc['is_verified'] = True
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)

    return {"user": user.model_dump(), "session_token": session_token, "message": "Account verified successfully!"}


@router.post("/auth/resend-verification-otp")
async def resend_verification_otp(request: Request):
    """Resend verification OTP for unverified accounts"""
    body = await request.json()
    email = body.get("email", "").strip().lower()

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Account not found")

    if user_doc.get('is_verified', True):
        raise HTTPException(status_code=400, detail="Account already verified")

    otp = await generate_otp(email)
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #f8fafc; border-radius: 16px;">
        <h2 style="color: #0ea5e9; margin-bottom: 16px;">Kaimera Learning - Account Verification</h2>
        <p style="color: #475569; font-size: 16px; margin-bottom: 24px;">Your verification code is:</p>
        <div style="background: white; border: 2px solid #e2e8f0; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0f172a;">{otp}</span>
        </div>
        <p style="color: #94a3b8; font-size: 14px;">This code expires in 10 minutes.</p>
    </div>
    """
    await send_email(email, "Kaimera Learning - Verify Your Account", html_content)

    return {"message": "Verification OTP resent to your email."}


# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
@router.post("/auth/google")
async def google_auth(request: Request, response: Response):
    """Authenticate with Google ID token"""
    body = await request.json()
    credential = body.get("credential")

    if not credential:
        raise HTTPException(status_code=400, detail="Google credential required")

    try:
        idinfo = id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        email = idinfo.get('email', '').lower()
        name = idinfo.get('name', '')
        picture = idinfo.get('picture')
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    # Find or create user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})

    if user_doc:
        if user_doc.get('is_blocked'):
            raise HTTPException(status_code=403, detail="Your account has been blocked by the administrator.")

        # Update name/picture
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "is_verified": True}}
        )
        user_id = user_doc['user_id']
    else:
        # Create new student account
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        from services.helpers import generate_student_code
        student_code = await generate_student_code()

        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": "student",
            "credits": 0.0,
            "picture": picture,
            "password_hash": None,
            "is_approved": True,
            "is_verified": True,
            "student_code": student_code,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)

    session_token = await create_session(user_id)

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)

    return {"user": user.model_dump(), "session_token": session_token}


@router.get("/auth/me")
async def get_me(request: Request, authorization: Optional[str] = Header(None)):
    """Get current user"""
    user = await get_current_user(request, authorization)
    return user.model_dump()


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get('session_token')
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})

    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}
