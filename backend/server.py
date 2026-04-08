from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import requests
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_api_key = os.environ['STRIPE_API_KEY']

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str  # student, teacher, admin
    credits: float = 0.0
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_approved: bool = True  # For teacher approval
    created_at: datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "student"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SessionData(BaseModel):
    session_id: str

class ClassSession(BaseModel):
    class_id: str
    teacher_id: str
    teacher_name: str
    title: str
    subject: str
    class_type: str  # "1:1" or "group"
    date: str  # ISO format
    start_time: str
    end_time: str
    credits_required: float
    max_students: int
    enrolled_students: List[Dict[str, str]] = []  # [{user_id, name}]
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    created_at: datetime

class ClassSessionCreate(BaseModel):
    title: str
    subject: str
    class_type: str
    date: str
    start_time: str
    end_time: str
    credits_required: float
    max_students: int

class BookingRequest(BaseModel):
    class_id: str

class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    type: str  # purchase, booking, refund
    amount: float
    description: str
    status: str  # completed, pending, failed
    created_at: datetime

class Feedback(BaseModel):
    feedback_id: str
    class_id: str
    student_id: str
    student_name: str
    teacher_id: str
    rating: int
    comments: str
    created_at: datetime

class FeedbackCreate(BaseModel):
    class_id: str
    student_id: str
    rating: int
    comments: str

class CreditAdjustment(BaseModel):
    user_id: str
    amount: float
    action: str  # add or deduct

class TeacherApproval(BaseModel):
    user_id: str
    approved: bool

class PaymentTransaction(BaseModel):
    payment_id: str
    user_id: str
    session_id: str
    amount: float
    currency: str
    payment_status: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

# ==================== HELPER FUNCTIONS ====================

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
        password_hash = hash_password("solidarity&peace2023")
        
        await db.users.insert_one({
            "user_id": admin_id,
            "email": admin_email,
            "name": "Kaimera Admin",
            "role": "admin",
            "credits": 0.0,
            "picture": None,
            "password_hash": password_hash,
            "is_approved": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        logging.info(f"Admin account seeded: {admin_email}")

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    """Register new user with email/password"""
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = hash_password(user_data.password)
    
    # Teachers start unapproved
    is_approved = True if user_data.role != "teacher" else False
    
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": user_data.role,
        "credits": 0.0,
        "picture": None,
        "password_hash": password_hash,
        "is_approved": is_approved,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Create session
    session_token = await create_session(user_id)
    
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    
    return {
        "user": user.model_dump(),
        "session_token": session_token,
        "message": "Registration successful" if is_approved else "Registration successful. Awaiting teacher approval."
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin, response: Response):
    """Login with email/password"""
    # Find user
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not user_doc.get('password_hash'):
        raise HTTPException(status_code=401, detail="This account uses Google login")
    
    if not verify_password(credentials.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_token = await create_session(user_doc['user_id'])
    
    # Set cookie
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

@api_router.post("/auth/session")
async def process_session(session_data: SessionData, response: Response):
    """Process Emergent Auth session_id and create user session"""
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    
    # Call Emergent Auth to get user data
    headers = {"X-Session-ID": session_data.session_id}
    try:
        resp = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        oauth_data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to validate session: {str(e)}")
    
    # Find or create user
    user_doc = await db.users.find_one({"email": oauth_data['email']}, {"_id": 0})
    
    if user_doc:
        # Update existing user
        await db.users.update_one(
            {"email": oauth_data['email']},
            {"$set": {
                "name": oauth_data['name'],
                "picture": oauth_data.get('picture')
            }}
        )
        user_id = user_doc['user_id']
    else:
        # Create new user (default to student)
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": oauth_data['email'],
            "name": oauth_data['name'],
            "role": "student",
            "credits": 0.0,
            "picture": oauth_data.get('picture'),
            "password_hash": None,
            "is_approved": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create our session
    session_token = await create_session(user_id)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    # Get fresh user data
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    
    return {"user": user.model_dump(), "session_token": session_token}

@api_router.get("/auth/me")
async def get_me(request: Request, authorization: Optional[str] = Header(None)):
    """Get current user"""
    user = await get_current_user(request, authorization)
    return user.model_dump()

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get('session_token')
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

# ==================== STUDENT ENDPOINTS ====================

@api_router.get("/classes/browse")
async def browse_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Browse available classes"""
    user = await get_current_user(request, authorization)
    
    # Get all scheduled classes
    classes = await db.class_sessions.find(
        {"status": "scheduled"},
        {"_id": 0}
    ).to_list(1000)
    
    # Convert datetime
    for cls in classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    
    return classes

@api_router.post("/classes/book")
async def book_class(booking: BookingRequest, request: Request, authorization: Optional[str] = Header(None)):
    """Book a class"""
    user = await get_current_user(request, authorization)
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can book classes")
    
    # Get class
    cls = await db.class_sessions.find_one({"class_id": booking.class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    if cls['status'] != "scheduled":
        raise HTTPException(status_code=400, detail="Class is not available for booking")
    
    # Check if already enrolled
    enrolled = any(s['user_id'] == user.user_id for s in cls['enrolled_students'])
    if enrolled:
        raise HTTPException(status_code=400, detail="Already enrolled in this class")
    
    # Check capacity
    if len(cls['enrolled_students']) >= cls['max_students']:
        raise HTTPException(status_code=400, detail="Class is full")
    
    # Check credits
    if user.credits < cls['credits_required']:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    # Deduct credits
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"credits": -cls['credits_required']}}
    )
    
    # Add student to class
    await db.class_sessions.update_one(
        {"class_id": booking.class_id},
        {"$push": {"enrolled_students": {"user_id": user.user_id, "name": user.name}}}
    )
    
    # Create transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "user_id": user.user_id,
        "type": "booking",
        "amount": cls['credits_required'],
        "description": f"Booked class: {cls['title']}",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Class booked successfully", "credits_remaining": user.credits - cls['credits_required']}

@api_router.post("/classes/cancel/{class_id}")
async def cancel_booking(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Cancel a class booking"""
    user = await get_current_user(request, authorization)
    
    # Get class
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if enrolled
    enrolled = any(s['user_id'] == user.user_id for s in cls['enrolled_students'])
    if not enrolled:
        raise HTTPException(status_code=400, detail="Not enrolled in this class")
    
    # Check if class has started
    class_datetime = datetime.fromisoformat(f"{cls['date']}T{cls['start_time']}:00")
    if class_datetime.tzinfo is None:
        class_datetime = class_datetime.replace(tzinfo=timezone.utc)
    
    if datetime.now(timezone.utc) >= class_datetime:
        raise HTTPException(status_code=400, detail="Cannot cancel after class start time")
    
    # Refund credits
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"credits": cls['credits_required']}}
    )
    
    # Remove student from class
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$pull": {"enrolled_students": {"user_id": user.user_id}}}
    )
    
    # Create refund transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "user_id": user.user_id,
        "type": "refund",
        "amount": cls['credits_required'],
        "description": f"Cancelled class: {cls['title']}",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Booking cancelled and credits refunded"}

@api_router.get("/student/dashboard")
async def student_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get student dashboard data"""
    user = await get_current_user(request, authorization)
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    
    # Get all classes where student is enrolled
    all_classes = await db.class_sessions.find(
        {"enrolled_students.user_id": user.user_id},
        {"_id": 0}
    ).to_list(1000)
    
    now = datetime.now(timezone.utc)
    upcoming = []
    past = []
    
    for cls in all_classes:
        class_datetime = datetime.fromisoformat(f"{cls['date']}T{cls['start_time']}:00")
        if class_datetime.tzinfo is None:
            class_datetime = class_datetime.replace(tzinfo=timezone.utc)
        
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
        
        if class_datetime > now:
            upcoming.append(cls)
        else:
            past.append(cls)
    
    return {
        "credits": user.credits,
        "upcoming_classes": upcoming,
        "past_classes": past
    }

# ==================== TEACHER ENDPOINTS ====================

@api_router.post("/classes/create")
async def create_class(class_data: ClassSessionCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Create a new class session"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Teacher account not approved yet")
    
    class_id = f"class_{uuid.uuid4().hex[:12]}"
    
    class_doc = {
        "class_id": class_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "title": class_data.title,
        "subject": class_data.subject,
        "class_type": class_data.class_type,
        "date": class_data.date,
        "start_time": class_data.start_time,
        "end_time": class_data.end_time,
        "credits_required": class_data.credits_required,
        "max_students": class_data.max_students,
        "enrolled_students": [],
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create a copy for insertion to avoid ObjectId in response
    insert_doc = class_doc.copy()
    await db.class_sessions.insert_one(insert_doc)
    
    # Convert datetime for response
    class_doc['created_at'] = datetime.fromisoformat(class_doc['created_at'])
    
    return {"message": "Class created successfully", "class": class_doc}

@api_router.get("/teacher/dashboard")
async def teacher_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher dashboard data"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    # Get all classes by this teacher
    classes = await db.class_sessions.find(
        {"teacher_id": user.user_id},
        {"_id": 0}
    ).to_list(1000)
    
    for cls in classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    
    return {
        "is_approved": user.is_approved,
        "classes": classes
    }

@api_router.post("/classes/start/{class_id}")
async def start_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Start a class"""
    user = await get_current_user(request, authorization)
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {"status": "in_progress"}}
    )
    
    return {"message": "Class started"}

@api_router.post("/feedback/submit")
async def submit_feedback(feedback_data: FeedbackCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Submit feedback for a student"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    # Get class and verify teacher
    cls = await db.class_sessions.find_one({"class_id": feedback_data.class_id}, {"_id": 0})
    if not cls or cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get student
    student = await db.users.find_one({"user_id": feedback_data.student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    feedback_id = f"feedback_{uuid.uuid4().hex[:12]}"
    
    feedback_doc = {
        "feedback_id": feedback_id,
        "class_id": feedback_data.class_id,
        "student_id": feedback_data.student_id,
        "student_name": student['name'],
        "teacher_id": user.user_id,
        "rating": feedback_data.rating,
        "comments": feedback_data.comments,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback_doc)
    
    return {"message": "Feedback submitted successfully"}

# ==================== ADMIN ENDPOINTS ====================

@api_router.post("/admin/approve-teacher")
async def approve_teacher(approval: TeacherApproval, request: Request, authorization: Optional[str] = Header(None)):
    """Approve or reject teacher"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    teacher = await db.users.find_one({"user_id": approval.user_id}, {"_id": 0})
    if not teacher or teacher['role'] != "teacher":
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    await db.users.update_one(
        {"user_id": approval.user_id},
        {"$set": {"is_approved": approval.approved}}
    )
    
    action = "approved" if approval.approved else "rejected"
    return {"message": f"Teacher {action} successfully"}

@api_router.get("/admin/teachers")
async def get_teachers(request: Request, authorization: Optional[str] = Header(None)):
    """Get all teachers"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    teachers = await db.users.find({"role": "teacher"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    for teacher in teachers:
        if isinstance(teacher['created_at'], str):
            teacher['created_at'] = datetime.fromisoformat(teacher['created_at'])
    
    return teachers

@api_router.get("/admin/classes")
async def get_all_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Get all classes"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    classes = await db.class_sessions.find({}, {"_id": 0}).to_list(1000)
    
    for cls in classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    
    return classes

@api_router.get("/admin/transactions")
async def get_transactions(request: Request, authorization: Optional[str] = Header(None)):
    """Get all transactions"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    transactions = await db.transactions.find({}, {"_id": 0}).to_list(1000)
    
    for txn in transactions:
        if isinstance(txn['created_at'], str):
            txn['created_at'] = datetime.fromisoformat(txn['created_at'])
    
    return transactions

@api_router.post("/admin/adjust-credits")
async def adjust_credits(adjustment: CreditAdjustment, request: Request, authorization: Optional[str] = Header(None)):
    """Adjust user credits"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    target_user = await db.users.find_one({"user_id": adjustment.user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if adjustment.action == "add":
        await db.users.update_one(
            {"user_id": adjustment.user_id},
            {"$inc": {"credits": adjustment.amount}}
        )
        description = f"Admin added {adjustment.amount} credits"
    else:
        await db.users.update_one(
            {"user_id": adjustment.user_id},
            {"$inc": {"credits": -adjustment.amount}}
        )
        description = f"Admin deducted {adjustment.amount} credits"
    
    # Create transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "user_id": adjustment.user_id,
        "type": "adjustment",
        "amount": adjustment.amount,
        "description": description,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Credits adjusted successfully"}

# ==================== STRIPE PAYMENT ENDPOINTS ====================

CREDIT_PACKAGES = {
    "small": {"credits": 10.0, "price": 10.0},
    "medium": {"credits": 25.0, "price": 20.0},
    "large": {"credits": 50.0, "price": 35.0}
}

@api_router.post("/payments/checkout")
async def create_checkout(package_id: str, origin_url: str, request: Request, authorization: Optional[str] = Header(None)):
    """Create Stripe checkout session for credits purchase"""
    user = await get_current_user(request, authorization)
    
    # Validate package
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    package = CREDIT_PACKAGES[package_id]
    
    # Build URLs from provided origin
    success_url = f"{origin_url}/payment-success?session_id={{{{CHECKOUT_SESSION_ID}}}}"
    cancel_url = f"{origin_url}/browse-classes"
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create checkout request
    checkout_request = CheckoutSessionRequest(
        amount=package['price'],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user.user_id,
            "package_id": package_id,
            "credits": str(package['credits'])
        }
    )
    
    # Create checkout session
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    payment_id = f"payment_{uuid.uuid4().hex[:12]}"
    await db.payment_transactions.insert_one({
        "payment_id": payment_id,
        "user_id": user.user_id,
        "session_id": session.session_id,
        "amount": package['price'],
        "currency": "usd",
        "payment_status": "pending",
        "status": "initiated",
        "metadata": {
            "package_id": package_id,
            "credits": package['credits']
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get payment status"""
    user = await get_current_user(request, authorization)
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Get checkout status
    checkout_status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Find payment transaction
    payment_doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    
    if not payment_doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Update payment status
    if checkout_status.payment_status == "paid" and payment_doc['payment_status'] != "paid":
        # Add credits (only once)
        credits = float(checkout_status.metadata.get('credits', 0))
        
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Update payment transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": "paid",
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Create transaction record
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        await db.transactions.insert_one({
            "transaction_id": transaction_id,
            "user_id": user.user_id,
            "type": "purchase",
            "amount": credits,
            "description": f"Purchased {credits} credits",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount": checkout_status.amount_total / 100,
        "currency": checkout_status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update payment transaction
        await db.payment_transactions.update_one(
            {"session_id": webhook_response.session_id},
            {"$set": {
                "payment_status": webhook_response.payment_status,
                "status": "completed" if webhook_response.payment_status == "paid" else "pending",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"received": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await seed_admin()
    logger.info("Kaimera Learning API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
