from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import requests
import resend
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_api_key = os.environ['STRIPE_API_KEY']

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

UPLOADS_DIR = ROOT_DIR / 'uploads' / 'learning_kits'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str  # student, teacher, admin, counsellor
    credits: float = 0.0
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_approved: bool = True  # For teacher approval
    phone: Optional[str] = None
    bio: Optional[str] = None  # Teacher profile bio
    institute: Optional[str] = None  # Student's institute
    goal: Optional[str] = None  # Student's goal
    preferred_time_slot: Optional[str] = None  # Student's preferred time
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    grade: Optional[str] = None  # Class level e.g. "9", "10", "12"
    teacher_code: Optional[str] = None  # Auto-generated for teachers e.g. KL-T0001
    bank_details: Optional[dict] = None  # {account_name, account_number, bank_name, ifsc_code}
    badges: Optional[list] = None  # Admin-assigned badges
    created_at: datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "student"
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    grade: Optional[str] = None

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
    max_students: int
    assigned_student_id: str  # REQUIRED - Teacher must select which student
    duration_days: int  # How many days this class will run
    is_demo: bool = False  # Whether this is a demo session

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

class StudentTeacherAssignment(BaseModel):
    assignment_id: str
    student_id: str
    student_name: str
    student_email: str
    teacher_id: str
    teacher_name: str
    teacher_email: str
    status: str  # pending, approved, rejected, expired
    credit_price: float  # Admin-set price per class for this student
    assigned_at: datetime
    approved_at: Optional[datetime] = None
    expires_at: datetime  # 24 hours from assignment

class AssignStudentToTeacher(BaseModel):
    student_id: str
    teacher_id: str

class TeacherApprovalRequest(BaseModel):
    assignment_id: str
    approved: bool

class SystemPricing(BaseModel):
    demo_price_student: float  # What student pays for demo
    class_price_student: float  # What student pays per class (can be overridden per student)
    demo_earning_teacher: float  # What teacher earns for demo
    class_earning_teacher: float  # What teacher earns per class

class CreateTeacherAccount(BaseModel):
    email: EmailStr
    password: str
    name: str

class UpdateTeacherProfile(BaseModel):
    bio: Optional[str] = None
    picture: Optional[str] = None
    bank_details: Optional[dict] = None  # {account_name, account_number, bank_name, ifsc_code}

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

class StudentProfileUpdate(BaseModel):
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    grade: Optional[str] = None

class ClassProofSubmit(BaseModel):
    class_id: str
    feedback_text: str
    student_performance: str  # excellent, good, average, needs_improvement
    topics_covered: str
    screenshot_base64: Optional[str] = None

class ProofVerification(BaseModel):
    proof_id: str
    approved: bool
    reviewer_notes: Optional[str] = None

class ComplaintCreate(BaseModel):
    subject: str
    description: str
    related_class_id: Optional[str] = None

class ComplaintResolve(BaseModel):
    complaint_id: str
    resolution: str
    status: str  # resolved or closed

class CreateStudentAccount(BaseModel):
    email: EmailStr
    password: str
    name: str
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    grade: Optional[str] = None

class DemoRequestCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    age: Optional[int] = None
    institute: Optional[str] = None
    preferred_date: str  # YYYY-MM-DD
    preferred_time_slot: str  # HH:MM
    message: Optional[str] = None

class DemoAssign(BaseModel):
    demo_id: str
    teacher_id: str

class DemoExtraGrant(BaseModel):
    email: EmailStr

class DemoFeedbackCreate(BaseModel):
    demo_id: str
    rating: int  # 1-5
    feedback_text: str
    preferred_teacher_id: Optional[str] = None

class TeacherFeedbackToStudent(BaseModel):
    student_id: str
    class_id: Optional[str] = None
    feedback_text: str
    performance_rating: str  # excellent, good, average, needs_improvement

class BadgeAssign(BaseModel):
    user_id: str
    badge_name: str

class AdminProofApproval(BaseModel):
    proof_id: str
    approved: bool
    admin_notes: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

async def generate_teacher_code():
    """Auto-generate unique teacher ID like KL-T0001"""
    await db.counters.update_one(
        {"counter_id": "teacher_code"},
        {"$inc": {"seq": 1}},
        upsert=True
    )
    doc = await db.counters.find_one({"counter_id": "teacher_code"}, {"_id": 0})
    return f"KL-T{doc['seq']:04d}"


async def generate_student_code():
    """Auto-generate unique student ID like KL-S0001"""
    await db.counters.update_one(
        {"counter_id": "student_code"},
        {"$inc": {"seq": 1}},
        upsert=True
    )
    doc = await db.counters.find_one({"counter_id": "student_code"}, {"_id": 0})
    return f"KL-S{doc['seq']:04d}"


async def send_email(to_email: str, subject: str, html_content: str):
    """Send email via Resend (non-blocking)"""
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return None

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
    """Register new user - ONLY creates students with 0 credits"""
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Force role to student - only students can self-register
    if user_data.role != "student":
        raise HTTPException(status_code=403, detail="Only students can self-register. Teachers are created by admin.")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = hash_password(user_data.password)
    
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": "student",  # Always student
        "credits": 0.0,  # Always start with 0 credits
        "picture": None,
        "password_hash": password_hash,
        "is_approved": True,
        "phone": user_data.phone,
        "bio": None,
        "institute": user_data.institute,
        "goal": user_data.goal,
        "preferred_time_slot": user_data.preferred_time_slot,
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
        "message": "Student account created successfully with 0 credits. Please contact admin to purchase credits."
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
    """Browse available classes - students only see classes created specifically for them"""
    user = await get_current_user(request, authorization)
    
    if user.role == "student":
        # Get approved teacher assignment for this student
        approved_assignment = await db.student_teacher_assignments.find_one(
            {"student_id": user.user_id, "status": "approved"},
            {"_id": 0}
        )
        
        if not approved_assignment:
            return []  # No approved teacher yet
        
        # Get classes created specifically for this student
        classes = await db.class_sessions.find(
            {
                "status": "scheduled",
                "teacher_id": approved_assignment['teacher_id'],
                "assigned_student_id": user.user_id  # Only classes created for this student
            },
            {"_id": 0}
        ).to_list(1000)
    else:
        # Admin/Teacher/Counsellor can see all classes
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
    """Book a class - uses admin-set custom price for the student"""
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
    
    # Get student-teacher assignment to get custom price
    assignment = await db.student_teacher_assignments.find_one({
        "student_id": user.user_id,
        "teacher_id": cls['teacher_id'],
        "status": "approved"
    }, {"_id": 0})
    
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this teacher")
    
    # Use custom price set by admin
    credits_to_deduct = assignment['credit_price']
    
    # Check credits
    if user.credits < credits_to_deduct:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    # Deduct credits
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"credits": -credits_to_deduct}}
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
        "amount": credits_to_deduct,
        "description": f"Booked class: {cls['title']} (Custom price: {credits_to_deduct} credits)",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Class booked successfully", "credits_remaining": user.credits - credits_to_deduct, "credits_deducted": credits_to_deduct}

@api_router.post("/classes/cancel/{class_id}")
async def cancel_booking(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Cancel a class booking - refunds custom price"""
    user = await get_current_user(request, authorization)
    
    # Get class
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if enrolled
    enrolled_student = None
    for s in cls['enrolled_students']:
        if s['user_id'] == user.user_id:
            enrolled_student = s
            break
    
    if not enrolled_student:
        raise HTTPException(status_code=400, detail="Not enrolled in this class")
    
    # Check if class has started
    class_datetime = datetime.fromisoformat(f"{cls['date']}T{cls['start_time']}:00")
    if class_datetime.tzinfo is None:
        class_datetime = class_datetime.replace(tzinfo=timezone.utc)
    
    if datetime.now(timezone.utc) >= class_datetime:
        raise HTTPException(status_code=400, detail="Cannot cancel after class start time")
    
    # Get assignment to find custom price
    assignment = await db.student_teacher_assignments.find_one({
        "student_id": user.user_id,
        "teacher_id": cls['teacher_id'],
        "status": "approved"
    }, {"_id": 0})
    
    refund_amount = assignment['credit_price'] if assignment else cls['credits_required']
    
    # Refund credits
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"credits": refund_amount}}
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
        "amount": refund_amount,
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
    """Create a new class session - teacher must select student"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Teacher account not approved yet")
    
    # Verify student is assigned to this teacher
    assignment = await db.student_teacher_assignments.find_one({
        "teacher_id": user.user_id,
        "student_id": class_data.assigned_student_id,
        "status": "approved"
    }, {"_id": 0})
    
    if not assignment:
        raise HTTPException(status_code=403, detail="Student not assigned to you or assignment not approved")
    
    # Get system pricing (admin-set, teacher doesn't decide)
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    if not pricing:
        raise HTTPException(status_code=500, detail="System pricing not configured")
    
    # Use demo price or custom assignment price
    if class_data.is_demo:
        credits_required = pricing.get('demo_price_student', 0)
    else:
        credits_required = assignment['credit_price']
    
    # Calculate end date based on duration
    start_date = datetime.fromisoformat(class_data.date)
    end_date = start_date + timedelta(days=class_data.duration_days - 1)  # -1 because start date counts as day 1
    
    class_id = f"class_{uuid.uuid4().hex[:12]}"
    
    class_doc = {
        "class_id": class_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "title": class_data.title,
        "subject": class_data.subject,
        "class_type": class_data.class_type,
        "is_demo": class_data.is_demo,
        "date": class_data.date,
        "end_date": end_date.isoformat().split('T')[0],  # End date
        "duration_days": class_data.duration_days,
        "start_time": class_data.start_time,
        "end_time": class_data.end_time,
        "credits_required": credits_required,  # From assignment, teacher doesn't see this
        "max_students": class_data.max_students,
        "assigned_student_id": class_data.assigned_student_id,  # Class created for specific student
        "enrolled_students": [],  # Will auto-enroll student after creation
        "status": "scheduled",
        "verification_status": "pending",  # pending, submitted, verified, rejected
        "cancellations": [],  # Tracks per-day cancellations by student
        "cancellation_count": 0,
        "max_cancellations": 3,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create a copy for insertion to avoid ObjectId in response
    insert_doc = class_doc.copy()
    await db.class_sessions.insert_one(insert_doc)
    
    # Auto-enroll the student (no booking needed for teacher-created classes)
    student = await db.users.find_one({"user_id": class_data.assigned_student_id}, {"_id": 0})
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$push": {"enrolled_students": {"user_id": student['user_id'], "name": student['name']}}}
    )
    
    # Deduct credits from student (auto-deduct for teacher-created classes)
    await db.users.update_one(
        {"user_id": student['user_id']},
        {"$inc": {"credits": -credits_required}}
    )
    
    # Create transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "user_id": student['user_id'],
        "type": "auto_booking",
        "amount": credits_required,
        "description": f"Auto-enrolled in class: {class_data.title}",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Don't return credits_required to teacher
    response_doc = {k: v for k, v in class_doc.items() if k != 'credits_required'}
    response_doc['created_at'] = datetime.fromisoformat(class_doc['created_at'])
    
    return {"message": "Class created successfully", "class": response_doc}

@api_router.get("/teacher/dashboard")
async def teacher_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher dashboard data with week view"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    # Get all classes by this teacher
    all_classes = await db.class_sessions.find(
        {"teacher_id": user.user_id},
        {"_id": 0}
    ).to_list(1000)
    
    for cls in all_classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    
    # Separate into this week's classes and others
    now = datetime.now(timezone.utc)
    today = now.date()
    # Start of week (Monday)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    this_week_classes = []
    other_classes = []
    
    for cls in all_classes:
        cls_date = datetime.fromisoformat(cls['date']).date() if isinstance(cls['date'], str) else cls['date']
        cls_end = datetime.fromisoformat(cls.get('end_date', cls['date'])).date() if isinstance(cls.get('end_date', cls['date']), str) else cls.get('end_date', cls_date)
        
        # Class overlaps with this week if its range intersects [week_start, week_end]
        if cls_date <= week_end and cls_end >= week_start and cls.get('status') != 'completed':
            this_week_classes.append(cls)
        else:
            other_classes.append(cls)
    
    # Get pending student assignments
    pending_assignments = await db.student_teacher_assignments.find(
        {"teacher_id": user.user_id, "status": "pending"},
        {"_id": 0}
    ).to_list(1000)
    
    for assignment in pending_assignments:
        if isinstance(assignment.get('assigned_at'), str):
            assignment['assigned_at'] = datetime.fromisoformat(assignment['assigned_at'])
        if isinstance(assignment.get('expires_at'), str):
            assignment['expires_at'] = datetime.fromisoformat(assignment['expires_at'])
    
    # Get approved students
    approved_students = await db.student_teacher_assignments.find(
        {"teacher_id": user.user_id, "status": "approved"},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "is_approved": user.is_approved,
        "classes": this_week_classes,
        "other_classes": other_classes,
        "pending_assignments": pending_assignments,
        "approved_students": approved_students
    }

@api_router.post("/teacher/approve-assignment")
async def approve_student_assignment(approval: TeacherApprovalRequest, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher approves or rejects student assignment"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    assignment = await db.student_teacher_assignments.find_one(
        {"assignment_id": approval.assignment_id},
        {"_id": 0}
    )
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if assignment['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    
    if assignment['status'] != "pending":
        raise HTTPException(status_code=400, detail="Assignment already processed")
    
    # Check if not expired
    expires_at = datetime.fromisoformat(assignment['expires_at'])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if datetime.now(timezone.utc) > expires_at:
        await db.student_teacher_assignments.update_one(
            {"assignment_id": approval.assignment_id},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Assignment expired")
    
    new_status = "approved" if approval.approved else "rejected"
    
    await db.student_teacher_assignments.update_one(
        {"assignment_id": approval.assignment_id},
        {"$set": {
            "status": new_status,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    action = "approved" if approval.approved else "rejected"
    return {"message": f"Student assignment {action}"}

@api_router.delete("/classes/delete/{class_id}")
async def delete_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher deletes a class"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    
    # Delete the class
    await db.class_sessions.delete_one({"class_id": class_id})
    
    return {"message": "Class deleted successfully"}

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

@api_router.post("/teacher/update-profile")
async def update_teacher_profile(profile_data: UpdateTeacherProfile, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher updates their profile - NO phone number allowed"""
    user = await get_current_user(request, authorization)
    
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    update_fields = {}
    if profile_data.bio is not None:
        update_fields['bio'] = profile_data.bio
    if profile_data.picture is not None:
        update_fields['picture'] = profile_data.picture
    if profile_data.bank_details is not None:
        update_fields['bank_details'] = profile_data.bank_details
    
    if update_fields:
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": update_fields}
        )
    
    return {"message": "Profile updated successfully"}

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
    
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    
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
    txn_type = "credit_add" if adjustment.action == "add" else "credit_deduct"
    await db.transactions.insert_one({
        "transaction_id": transaction_id,
        "user_id": adjustment.user_id,
        "type": txn_type,
        "amount": adjustment.amount,
        "description": description,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Credits adjusted successfully"}

@api_router.post("/admin/assign-student")
async def assign_student_to_teacher(assignment: AssignStudentToTeacher, request: Request, authorization: Optional[str] = Header(None)):
    """Admin or Counsellor assigns student to teacher"""
    user = await get_current_user(request, authorization)
    
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    
    # Get student and teacher details
    student = await db.users.find_one({"user_id": assignment.student_id, "role": "student"}, {"_id": 0})
    teacher = await db.users.find_one({"user_id": assignment.teacher_id, "role": "teacher"}, {"_id": 0})
    
    if not student or not teacher:
        raise HTTPException(status_code=404, detail="Student or teacher not found")
    
    # CRITICAL: Check if student already has an active assignment (one student, one teacher only)
    existing_active = await db.student_teacher_assignments.find_one({
        "student_id": assignment.student_id,
        "status": {"$in": ["pending", "approved"]}  # Only pending or approved block new assignments
    }, {"_id": 0})
    
    if existing_active:
        raise HTTPException(status_code=400, detail=f"Student already assigned to {existing_active['teacher_name']}. Only one teacher per student allowed.")
    
    # Rejected assignments don't block - student can be reassigned to a different teacher
    
    # Get system pricing (admin-set, counsellor cannot override)
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    credit_price = pricing.get("class_price_student", 0) if pricing else 0
    
    assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
    assigned_at = datetime.now(timezone.utc)
    expires_at = assigned_at + timedelta(hours=24)
    
    assignment_doc = {
        "assignment_id": assignment_id,
        "student_id": assignment.student_id,
        "student_name": student['name'],
        "student_email": student['email'],
        "teacher_id": assignment.teacher_id,
        "teacher_name": teacher['name'],
        "teacher_email": teacher['email'],
        "status": "pending",
        "credit_price": credit_price,
        "assigned_at": assigned_at.isoformat(),
        "approved_at": None,
        "expires_at": expires_at.isoformat(),
        "assigned_by": user.user_id  # Track who assigned
    }
    
    await db.student_teacher_assignments.insert_one(assignment_doc)
    
    return {"message": "Student assigned to teacher. Teacher has 24 hours to approve.", "assignment_id": assignment_id}

@api_router.get("/admin/emergency-assignments")
async def get_emergency_assignments(request: Request, authorization: Optional[str] = Header(None)):
    """Get assignments that expired without teacher approval"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    # Check for expired pending assignments
    now = datetime.now(timezone.utc)
    
    # Find pending assignments past expiry
    pending_assignments = await db.student_teacher_assignments.find({
        "status": "pending"
    }, {"_id": 0}).to_list(1000)
    
    emergency_assignments = []
    for assignment in pending_assignments:
        expires_at = datetime.fromisoformat(assignment['expires_at'])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            # Mark as expired
            await db.student_teacher_assignments.update_one(
                {"assignment_id": assignment['assignment_id']},
                {"$set": {"status": "expired"}}
            )
            assignment['status'] = "expired"
            emergency_assignments.append(assignment)
    
    return emergency_assignments

@api_router.get("/admin/all-assignments")
async def get_all_assignments(request: Request, authorization: Optional[str] = Header(None)):
    """Get all student-teacher assignments"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    assignments = await db.student_teacher_assignments.find({}, {"_id": 0}).to_list(1000)
    
    for assignment in assignments:
        for field in ['assigned_at', 'expires_at']:
            if assignment.get(field) and isinstance(assignment[field], str):
                assignment[field] = datetime.fromisoformat(assignment[field])
        if assignment.get('approved_at') and isinstance(assignment['approved_at'], str):
            assignment['approved_at'] = datetime.fromisoformat(assignment['approved_at'])
    
    return assignments

@api_router.get("/admin/students")
async def get_all_students(request: Request, authorization: Optional[str] = Header(None)):
    """Get all students"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    for student in students:
        if isinstance(student.get('created_at'), str):
            student['created_at'] = datetime.fromisoformat(student['created_at'])
    
    return students

@api_router.post("/admin/create-teacher")
async def create_teacher_account(teacher_data: CreateTeacherAccount, request: Request, authorization: Optional[str] = Header(None)):
    """Admin creates teacher account"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    # Check if email exists
    existing = await db.users.find_one({"email": teacher_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create teacher
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = hash_password(teacher_data.password)
    teacher_code = await generate_teacher_code()
    
    teacher_doc = {
        "user_id": user_id,
        "email": teacher_data.email,
        "name": teacher_data.name,
        "role": "teacher",
        "credits": 0.0,  # Teacher starts with 0, earns through classes
        "picture": None,
        "password_hash": password_hash,
        "is_approved": True,  # Admin-created teachers are auto-approved
        "phone": None,
        "bio": None,
        "teacher_code": teacher_code,
        "bank_details": None,
        "badges": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(teacher_doc)
    
    return {"message": "Teacher account created successfully", "user_id": user_id, "email": teacher_data.email, "teacher_code": teacher_code}

@api_router.post("/admin/create-counsellor")
async def create_counsellor_account(counsellor_data: CreateTeacherAccount, request: Request, authorization: Optional[str] = Header(None)):
    """Admin creates counsellor account"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    # Check if email exists
    existing = await db.users.find_one({"email": counsellor_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create counsellor
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = hash_password(counsellor_data.password)
    
    counsellor_doc = {
        "user_id": user_id,
        "email": counsellor_data.email,
        "name": counsellor_data.name,
        "role": "counsellor",
        "credits": 0.0,
        "picture": None,
        "password_hash": password_hash,
        "is_approved": True,
        "phone": None,
        "bio": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(counsellor_doc)
    
    return {"message": "Counsellor account created successfully", "user_id": user_id, "email": counsellor_data.email}

@api_router.post("/admin/set-pricing")
async def set_system_pricing(pricing: SystemPricing, request: Request, authorization: Optional[str] = Header(None)):
    """Admin sets system-wide pricing"""
    user = await get_current_user(request, authorization)
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    pricing_doc = {
        "pricing_id": "system_pricing",  # Single document for system pricing
        "demo_price_student": pricing.demo_price_student,
        "class_price_student": pricing.class_price_student,
        "demo_earning_teacher": pricing.demo_earning_teacher,
        "class_earning_teacher": pricing.class_earning_teacher,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user.user_id
    }
    
    # Upsert pricing
    await db.system_pricing.update_one(
        {"pricing_id": "system_pricing"},
        {"$set": pricing_doc},
        upsert=True
    )
    
    return {"message": "System pricing updated successfully"}

@api_router.get("/admin/get-pricing")
async def get_system_pricing(request: Request, authorization: Optional[str] = Header(None)):
    """Get current system pricing"""
    user = await get_current_user(request, authorization)
    
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    
    if not pricing:
        # Return default pricing if not set
        return {
            "demo_price_student": 0.0,
            "class_price_student": 0.0,
            "demo_earning_teacher": 0.0,
            "class_earning_teacher": 0.0
        }
    
    if isinstance(pricing.get('updated_at'), str):
        pricing['updated_at'] = datetime.fromisoformat(pricing['updated_at'])
    
    return pricing

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
    """Handle Stripe webhooks - credits user account on successful payment"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Find payment transaction
        payment_doc = await db.payment_transactions.find_one(
            {"session_id": webhook_response.session_id}, {"_id": 0}
        )
        
        # Update payment transaction
        await db.payment_transactions.update_one(
            {"session_id": webhook_response.session_id},
            {"$set": {
                "payment_status": webhook_response.payment_status,
                "status": "completed" if webhook_response.payment_status == "paid" else "pending",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # If paid, credit the user
        if webhook_response.payment_status == "paid" and payment_doc and payment_doc['payment_status'] != "paid":
            user_id = payment_doc.get('user_id')
            credits = float(payment_doc['metadata'].get('credits', 0))
            
            if user_id and credits > 0:
                await db.users.update_one(
                    {"user_id": user_id},
                    {"$inc": {"credits": credits}}
                )
                
                transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
                await db.transactions.insert_one({
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "type": "purchase",
                    "amount": credits,
                    "description": f"Purchased {credits} credits via Stripe",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
                logging.info(f"Webhook: Credited {credits} to user {user_id}")
        
        return {"received": True}
    except Exception as e:
        logging.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==================== COUNSELLOR ENDPOINTS ====================

@api_router.get("/counsellor/dashboard")
async def counsellor_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get counsellor dashboard data"""
    user = await get_current_user(request, authorization)
    
    if user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counsellor access only")
    
    # Get all students
    all_students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    # Get all active assignments (pending or approved)
    active_assignments = await db.student_teacher_assignments.find(
        {"status": {"$in": ["pending", "approved"]}},
        {"_id": 0}
    ).to_list(1000)
    
    # Get rejected assignments
    rejected_assignments = await db.student_teacher_assignments.find(
        {"status": "rejected"},
        {"_id": 0}
    ).to_list(1000)
    
    # Filter out students who already have active assignments
    assigned_student_ids = set([a['student_id'] for a in active_assignments])
    unassigned_students = [s for s in all_students if s['user_id'] not in assigned_student_ids]
    
    # Get all teachers
    teachers = await db.users.find({"role": "teacher", "is_approved": True}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    return {
        "unassigned_students": unassigned_students,  # Only students without active assignments
        "all_students": all_students,  # For separate page
        "teachers": teachers,
        "active_assignments": active_assignments,
        "rejected_assignments": rejected_assignments
    }

# ==================== STUDENT PROFILE ENDPOINTS ====================

@api_router.post("/student/update-profile")
async def update_student_profile(profile: StudentProfileUpdate, request: Request, authorization: Optional[str] = Header(None)):
    """Student updates their profile details"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    
    update_fields = {}
    if profile.institute is not None:
        update_fields['institute'] = profile.institute
    if profile.goal is not None:
        update_fields['goal'] = profile.goal
    if profile.preferred_time_slot is not None:
        update_fields['preferred_time_slot'] = profile.preferred_time_slot
    if profile.phone is not None:
        update_fields['phone'] = profile.phone
    if profile.state is not None:
        update_fields['state'] = profile.state
    if profile.city is not None:
        update_fields['city'] = profile.city
    if profile.country is not None:
        update_fields['country'] = profile.country
    if profile.grade is not None:
        update_fields['grade'] = profile.grade
    
    if update_fields:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update_fields})
    
    return {"message": "Profile updated successfully"}

@api_router.get("/counsellor/student-profile/{student_id}")
async def get_student_profile(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get detailed student profile for counsellor view"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    student = await db.users.find_one({"user_id": student_id, "role": "student"}, {"_id": 0, "password_hash": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get assignment info
    assignment = await db.student_teacher_assignments.find_one(
        {"student_id": student_id, "status": {"$in": ["pending", "approved"]}},
        {"_id": 0}
    )
    
    # Get class history
    classes = await db.class_sessions.find(
        {"enrolled_students.user_id": student_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "student": student,
        "current_assignment": assignment,
        "class_history": classes
    }

# ==================== CLASS PROOF/VERIFICATION ENDPOINTS ====================

@api_router.post("/teacher/submit-proof")
async def submit_class_proof(proof: ClassProofSubmit, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher submits proof after completing a class"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    cls = await db.class_sessions.find_one({"class_id": proof.class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    
    # Check if proof already submitted
    existing = await db.class_proofs.find_one({"class_id": proof.class_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Proof already submitted for this class")
    
    proof_id = f"proof_{uuid.uuid4().hex[:12]}"
    proof_doc = {
        "proof_id": proof_id,
        "class_id": proof.class_id,
        "class_title": cls['title'],
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "student_id": cls.get('assigned_student_id', ''),
        "feedback_text": proof.feedback_text,
        "student_performance": proof.student_performance,
        "topics_covered": proof.topics_covered,
        "screenshot_base64": proof.screenshot_base64,
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "reviewer_notes": None
    }
    
    await db.class_proofs.insert_one(proof_doc)
    
    # Update class verification status
    await db.class_sessions.update_one(
        {"class_id": proof.class_id},
        {"$set": {"verification_status": "submitted"}}
    )
    
    return {"message": "Proof submitted successfully", "proof_id": proof_id}

@api_router.get("/teacher/my-proofs")
async def get_teacher_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all proofs submitted by this teacher"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    proofs = await db.class_proofs.find(
        {"teacher_id": user.user_id},
        {"_id": 0, "screenshot_base64": 0}
    ).to_list(1000)
    
    return proofs

@api_router.get("/counsellor/pending-proofs")
async def get_pending_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all pending class proofs for counsellor verification"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    proofs = await db.class_proofs.find(
        {"status": "pending"},
        {"_id": 0}
    ).to_list(1000)
    
    return proofs

@api_router.get("/counsellor/all-proofs")
async def get_all_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all class proofs"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    proofs = await db.class_proofs.find({}, {"_id": 0}).to_list(1000)
    return proofs

@api_router.post("/counsellor/verify-proof")
async def verify_class_proof(verification: ProofVerification, request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor verifies a class proof - if approved, forwards to Admin"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    proof = await db.class_proofs.find_one({"proof_id": verification.proof_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof['status'] != "pending":
        raise HTTPException(status_code=400, detail="Proof already processed")
    
    new_status = "verified" if verification.approved else "rejected"
    
    update_data = {
        "status": new_status,
        "reviewed_by": user.user_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_notes": verification.reviewer_notes
    }
    # If counsellor approves, set admin_status to pending for admin review
    if verification.approved:
        update_data["admin_status"] = "pending"
    
    await db.class_proofs.update_one(
        {"proof_id": verification.proof_id},
        {"$set": update_data}
    )
    
    # Update class verification status
    await db.class_sessions.update_one(
        {"class_id": proof['class_id']},
        {"$set": {"verification_status": new_status}}
    )
    
    # If counsellor approved, notify admin(s) for final approval
    if verification.approved:
        admins = await db.users.find({"role": "admin"}, {"_id": 0}).to_list(10)
        for admin in admins:
            await db.notifications.insert_one({
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": admin["user_id"],
                "type": "proof_for_admin_review",
                "title": "Proof Awaiting Your Approval",
                "message": f"Counsellor {user.name} approved proof for class '{proof.get('class_title', '')}'. Credit pending your approval.",
                "read": False,
                "related_id": verification.proof_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    action = "approved (forwarded to Admin)" if verification.approved else "rejected"
    return {"message": f"Proof {action} successfully"}

# ==================== COMPLAINT ENDPOINTS ====================

@api_router.post("/complaints/create")
async def create_complaint(complaint: ComplaintCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Create a new complaint"""
    user = await get_current_user(request, authorization)
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin cannot create complaints")
    
    # If student, auto-link to their assigned teacher
    related_teacher_id = None
    if user.role == "student":
        assignment = await db.student_teacher_assignments.find_one(
            {"student_id": user.user_id, "status": {"$in": ["pending", "approved"]}},
            {"_id": 0}
        )
        if assignment:
            related_teacher_id = assignment.get("teacher_id")
    
    complaint_id = f"complaint_{uuid.uuid4().hex[:12]}"
    complaint_doc = {
        "complaint_id": complaint_id,
        "raised_by": user.user_id,
        "raised_by_name": user.name,
        "raised_by_role": user.role,
        "related_teacher_id": related_teacher_id,
        "subject": complaint.subject,
        "description": complaint.description,
        "related_class_id": complaint.related_class_id,
        "status": "open",
        "resolution": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None
    }
    
    await db.complaints.insert_one(complaint_doc)
    
    # Notify teacher if student complaint
    if related_teacher_id:
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        await db.notifications.insert_one({
            "notification_id": notif_id,
            "user_id": related_teacher_id,
            "type": "complaint_received",
            "title": "Student Complaint",
            "message": f"{user.name} raised a complaint: {complaint.subject}",
            "read": False,
            "related_id": complaint_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"message": "Complaint submitted successfully", "complaint_id": complaint_id}

@api_router.get("/complaints/my")
async def get_my_complaints(request: Request, authorization: Optional[str] = Header(None)):
    """Get complaints raised by current user"""
    user = await get_current_user(request, authorization)
    complaints = await db.complaints.find(
        {"raised_by": user.user_id},
        {"_id": 0}
    ).to_list(1000)
    return complaints

@api_router.get("/admin/complaints")
async def get_all_complaints(request: Request, authorization: Optional[str] = Header(None)):
    """Admin/Counsellor views all complaints"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    
    complaints = await db.complaints.find({}, {"_id": 0}).to_list(1000)
    return complaints

@api_router.post("/admin/resolve-complaint")
async def resolve_complaint(resolution: ComplaintResolve, request: Request, authorization: Optional[str] = Header(None)):
    """Admin resolves a complaint"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    complaint = await db.complaints.find_one({"complaint_id": resolution.complaint_id}, {"_id": 0})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    await db.complaints.update_one(
        {"complaint_id": resolution.complaint_id},
        {"$set": {
            "status": resolution.status,
            "resolution": resolution.resolution,
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Complaint {resolution.status}"}

# ==================== AUTO-REASSIGNMENT ENDPOINTS ====================

@api_router.get("/counsellor/expired-classes")
async def get_expired_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Get classes whose duration has ended for reassignment decisions"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')
    
    # Find classes with end_date in the past
    all_classes = await db.class_sessions.find(
        {"status": "scheduled"},
        {"_id": 0}
    ).to_list(10000)
    
    expired_classes = []
    for cls in all_classes:
        end_date_str = cls.get('end_date', cls['date'])
        if end_date_str < today_str:
            # Calculate days since expiry
            end_date = datetime.fromisoformat(end_date_str)
            days_since = (now - end_date.replace(tzinfo=timezone.utc)).days
            cls['days_since_expiry'] = days_since
            cls['can_rebook'] = days_since <= 3  # Within 3 working days
            expired_classes.append(cls)
    
    return expired_classes

@api_router.post("/counsellor/reassign-student")
async def reassign_student(data: Dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor reassigns or releases a student after class duration ends"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    student_id = data.get('student_id')
    action = data.get('action')  # 'rebook' or 'release'
    
    if action == "release":
        # Set current assignment to expired, making student available for reassignment
        await db.student_teacher_assignments.update_many(
            {"student_id": student_id, "status": "approved"},
            {"$set": {"status": "completed"}}
        )
        return {"message": "Student released for reassignment"}
    elif action == "rebook":
        # Keep the current assignment active (no change needed)
        return {"message": "Student kept with current teacher for rebooking"}
    
    raise HTTPException(status_code=400, detail="Invalid action")

# ==================== CANCEL CLASS DAY ENDPOINT ====================

@api_router.post("/classes/cancel-day/{class_id}")
async def cancel_class_day(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Student cancels class for a day - extends duration, max 3 cancellations"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls.get('assigned_student_id') != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    if cls['status'] != 'scheduled':
        raise HTTPException(status_code=400, detail="Class is not active")
    
    cancellation_count = cls.get('cancellation_count', 0)
    max_cancellations = cls.get('max_cancellations', 3)
    
    if cancellation_count >= max_cancellations:
        # Dismiss the class
        await db.class_sessions.update_one(
            {"class_id": class_id},
            {"$set": {"status": "dismissed"}}
        )
        # Notify teacher
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        await db.notifications.insert_one({
            "notification_id": notif_id,
            "user_id": cls['teacher_id'],
            "type": "class_dismissed",
            "title": "Class Dismissed",
            "message": f"Class '{cls['title']}' has been dismissed. {user.name} exceeded max cancellations ({max_cancellations}).",
            "read": False,
            "related_id": class_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=400, detail="Maximum cancellations reached. Class has been dismissed.")
    
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check if already cancelled for today
    existing_cancellations = cls.get('cancellations', [])
    for c in existing_cancellations:
        if c.get('date') == today_str:
            raise HTTPException(status_code=400, detail="Already cancelled for today")
    
    # Add cancellation record and extend end_date by 1 day
    cancellation_record = {
        "date": today_str,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "student_id": user.user_id
    }
    
    # Extend end_date by 1 day
    current_end_date = datetime.fromisoformat(cls.get('end_date', cls['date']))
    new_end_date = current_end_date + timedelta(days=1)
    new_duration = cls.get('duration_days', 1) + 1
    new_count = cancellation_count + 1
    
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {
            "$push": {"cancellations": cancellation_record},
            "$set": {
                "cancellation_count": new_count,
                "end_date": new_end_date.strftime('%Y-%m-%d'),
                "duration_days": new_duration
            }
        }
    )
    
    # Notify teacher
    notif_id = f"notif_{uuid.uuid4().hex[:12]}"
    await db.notifications.insert_one({
        "notification_id": notif_id,
        "user_id": cls['teacher_id'],
        "type": "class_cancelled_day",
        "title": "Class Cancelled Today",
        "message": f"{user.name} cancelled today's session of '{cls['title']}'. Class extended by 1 day. ({new_count}/{max_cancellations} cancellations used)",
        "read": False,
        "related_id": class_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    remaining = max_cancellations - new_count
    return {
        "message": f"Class cancelled for today. Duration extended by 1 day. {remaining} cancellations remaining.",
        "cancellation_count": new_count,
        "remaining_cancellations": remaining,
        "new_end_date": new_end_date.strftime('%Y-%m-%d')
    }

# ==================== ADMIN CREATE STUDENT ENDPOINT ====================

@api_router.post("/admin/create-student")
async def admin_create_student(student_data: CreateStudentAccount, request: Request, authorization: Optional[str] = Header(None)):
    """Admin creates a student account manually"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    existing = await db.users.find_one({"email": student_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = bcrypt.hashpw(student_data.password.encode('utf-8'), bcrypt.gensalt(int(os.environ.get('BCRYPT_ROUNDS', 12)))).decode('utf-8')
    student_code = await generate_student_code()
    
    student_doc = {
        "user_id": user_id,
        "email": student_data.email,
        "name": student_data.name,
        "role": "student",
        "credits": 0.0,
        "picture": None,
        "password_hash": password_hash,
        "is_approved": True,
        "phone": student_data.phone,
        "bio": None,
        "institute": student_data.institute,
        "goal": student_data.goal,
        "preferred_time_slot": student_data.preferred_time_slot,
        "state": student_data.state,
        "city": student_data.city,
        "country": student_data.country,
        "grade": student_data.grade,
        "student_code": student_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(student_doc)
    
    return {
        "message": "Student account created successfully",
        "user_id": user_id,
        "email": student_data.email,
        "name": student_data.name,
        "student_code": student_code,
        "credentials": {
            "email": student_data.email,
            "password": student_data.password
        }
    }

# ==================== NOTIFICATION ENDPOINTS ====================

@api_router.get("/notifications/my")
async def get_my_notifications(request: Request, authorization: Optional[str] = Header(None)):
    """Get notifications for the current user"""
    user = await get_current_user(request, authorization)
    notifications = await db.notifications.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return notifications

@api_router.post("/notifications/mark-read/{notification_id}")
async def mark_notification_read(notification_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Mark a notification as read"""
    user = await get_current_user(request, authorization)
    await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user.user_id},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(request: Request, authorization: Optional[str] = Header(None)):
    """Mark all notifications as read"""
    user = await get_current_user(request, authorization)
    await db.notifications.update_many(
        {"user_id": user.user_id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}

# ==================== CLASS LIFECYCLE ENDPOINTS ====================

@api_router.post("/classes/start/{class_id}")
async def start_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher starts a class session - opens the video room"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    if cls['status'] not in ['scheduled', 'in_progress']:
        raise HTTPException(status_code=400, detail=f"Cannot start class with status: {cls['status']}")
    
    room_id = f"kaimera-{class_id}"
    
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {
            "status": "in_progress",
            "room_id": room_id,
            "last_started_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify enrolled students
    for student in cls.get('enrolled_students', []):
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        await db.notifications.insert_one({
            "notification_id": notif_id,
            "user_id": student['user_id'],
            "type": "class_started",
            "title": "Class Started!",
            "message": f"'{cls['title']}' has started. Join now!",
            "read": False,
            "related_id": class_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"message": "Class started", "room_id": room_id}

@api_router.post("/classes/end/{class_id}")
async def end_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher ends a class session"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    
    # Check if today is the last day or past end_date
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    end_date_str = cls.get('end_date', cls['date'])
    
    if today_str >= end_date_str:
        new_status = "completed"
    else:
        new_status = "scheduled"
    
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {
            "status": new_status,
            "room_id": None,
            "last_ended_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Class ended. Status: {new_status}", "status": new_status}

@api_router.get("/classes/status/{class_id}")
async def get_class_status(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get class current status and room info"""
    user = await get_current_user(request, authorization)
    
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return {
        "class_id": cls['class_id'],
        "title": cls['title'],
        "status": cls['status'],
        "room_id": cls.get('room_id'),
        "teacher_id": cls['teacher_id'],
        "teacher_name": cls['teacher_name'],
        "is_in_progress": cls['status'] == 'in_progress'
    }

# ==================== TEACHER STUDENT COMPLAINTS ====================

@api_router.get("/teacher/student-complaints")
async def get_teacher_student_complaints(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher sees complaints from their assigned students"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    complaints = await db.complaints.find(
        {"related_teacher_id": user.user_id},
        {"_id": 0}
    ).to_list(1000)
    return complaints

# ==================== DEMO BOOKING ENDPOINTS ====================

@api_router.post("/demo/request")
async def create_demo_request(demo_data: DemoRequestCreate):
    """Public endpoint - anyone can request a demo (no auth required)"""
    existing_demos = await db.demo_requests.count_documents({"email": demo_data.email})
    max_demos = 3
    extra = await db.demo_extras.find_one({"email": demo_data.email}, {"_id": 0})
    if extra:
        max_demos += extra.get("extra_count", 0)
    if existing_demos >= max_demos:
        raise HTTPException(status_code=400, detail=f"Maximum {max_demos} demo requests reached for this email. Contact admin for an additional chance.")

    demo_id = f"demo_{uuid.uuid4().hex[:12]}"
    existing_user = await db.users.find_one({"email": demo_data.email}, {"_id": 0})

    demo_doc = {
        "demo_id": demo_id,
        "name": demo_data.name,
        "email": demo_data.email,
        "phone": demo_data.phone,
        "age": demo_data.age,
        "institute": demo_data.institute,
        "preferred_date": demo_data.preferred_date,
        "preferred_time_slot": demo_data.preferred_time_slot,
        "message": demo_data.message,
        "status": "pending",
        "student_user_id": existing_user["user_id"] if existing_user else None,
        "accepted_by_teacher_id": None,
        "accepted_by_teacher_name": None,
        "assigned_by": None,
        "assigned_teacher_id": None,
        "assigned_teacher_name": None,
        "class_id": None,
        "demo_number": existing_demos + 1,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_doc = demo_doc.copy()
    await db.demo_requests.insert_one(insert_doc)

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_requested",
        "actor_name": demo_data.name,
        "actor_email": demo_data.email,
        "actor_id": existing_user["user_id"] if existing_user else None,
        "actor_role": "student",
        "target_type": "demo",
        "target_id": demo_id,
        "related_student_id": existing_user["user_id"] if existing_user else None,
        "related_student_name": demo_data.name,
        "details": f"{demo_data.name} requested demo #{existing_demos + 1} for {demo_data.preferred_date} at {demo_data.preferred_time_slot}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Demo request submitted successfully!", "demo_id": demo_id}


@api_router.get("/demo/live-sheet")
async def get_demo_live_sheet(request: Request, authorization: Optional[str] = Header(None)):
    """Get all pending demo requests - visible to teachers and counsellors"""
    user = await get_current_user(request, authorization)
    if user.role not in ["teacher", "counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    demos = await db.demo_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)

    # For counsellors, also return list of available teachers
    teachers = []
    if user.role in ["counsellor", "admin"]:
        teachers = await db.users.find(
            {"role": "teacher", "is_approved": True},
            {"_id": 0, "password_hash": 0}
        ).to_list(1000)

    return {"demos": demos, "teachers": teachers}


async def _create_demo_class(demo: dict, teacher_user_id: str, teacher_name: str):
    """Shared helper to create a demo class from a demo request"""
    # Ensure student account exists
    student = await db.users.find_one({"email": demo["email"]}, {"_id": 0})
    temp_password = None

    if not student:
        student_id = f"user_{uuid.uuid4().hex[:12]}"
        temp_password = f"demo{uuid.uuid4().hex[:8]}"
        password_hash_val = hash_password(temp_password)
        student = {
            "user_id": student_id,
            "email": demo["email"],
            "name": demo["name"],
            "role": "student",
            "credits": 0.0,
            "picture": None,
            "password_hash": password_hash_val,
            "is_approved": True,
            "phone": demo.get("phone"),
            "bio": None,
            "institute": demo.get("institute"),
            "goal": None,
            "preferred_time_slot": demo.get("preferred_time_slot"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        insert_student = student.copy()
        await db.users.insert_one(insert_student)
    else:
        student_id = student["user_id"]

    # Get demo pricing
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    demo_price = pricing.get("demo_price_student", 0) if pricing else 0

    # Parse time
    preferred_time = demo.get("preferred_time_slot", "10:00")
    try:
        parts = preferred_time.split(":")
        hour = int(parts[0])
        minute = parts[1] if len(parts) > 1 else "00"
        end_time = f"{hour + 1:02d}:{minute}"
    except Exception:
        preferred_time = "10:00"
        end_time = "11:00"

    class_id = f"class_{uuid.uuid4().hex[:12]}"
    class_doc = {
        "class_id": class_id,
        "teacher_id": teacher_user_id,
        "teacher_name": teacher_name,
        "title": f"Demo Session - {demo['name']}",
        "subject": "Demo",
        "class_type": "1:1",
        "is_demo": True,
        "date": demo["preferred_date"],
        "end_date": demo["preferred_date"],
        "duration_days": 1,
        "start_time": preferred_time,
        "end_time": end_time,
        "credits_required": demo_price,
        "max_students": 1,
        "assigned_student_id": student_id,
        "enrolled_students": [{"user_id": student_id, "name": demo["name"]}],
        "status": "scheduled",
        "verification_status": "pending",
        "cancellations": [],
        "cancellation_count": 0,
        "max_cancellations": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_class = class_doc.copy()
    await db.class_sessions.insert_one(insert_class)

    # Deduct demo credits if applicable
    if demo_price > 0:
        await db.users.update_one(
            {"user_id": student_id},
            {"$inc": {"credits": -demo_price}}
        )
        await db.transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": student_id,
            "type": "demo_booking",
            "amount": demo_price,
            "description": f"Demo class with {teacher_name}",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    # In-app notification for student
    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": student_id,
        "type": "demo_accepted",
        "title": "Demo Session Confirmed!",
        "message": f"Your demo has been accepted by {teacher_name}. Scheduled: {demo['preferred_date']} at {preferred_time}.",
        "read": False,
        "related_id": class_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Email notification to student
    await send_email(
        demo["email"],
        "Your Demo Session is Confirmed! - Kaimera Learning",
        f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#0ea5e9,#8b5cf6);padding:30px;border-radius:16px;color:#fff;text-align:center;">
            <h1 style="margin:0;font-size:24px;">Demo Confirmed!</h1>
        </div>
        <div style="padding:20px;background:#f8fafc;border-radius:0 0 16px 16px;">
            <p>Hi <strong>{demo['name']}</strong>,</p>
            <p>Great news! Your demo session has been accepted by <strong>{teacher_name}</strong>.</p>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Date</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{demo['preferred_date']}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Time</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{preferred_time}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Teacher</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{teacher_name}</td></tr>
            </table>
            {f'<p style="background:#fef3c7;padding:12px;border-radius:8px;">Your login: <strong>{demo["email"]}</strong> / <strong>{temp_password}</strong></p>' if temp_password else ''}
            <p style="color:#64748b;font-size:14px;">Log in to your dashboard to join the class when it's time.</p>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:16px;">Kaimera Learning</p>
        </div>"""
    )

    return class_id, student_id, temp_password


@api_router.post("/demo/accept/{demo_id}")
async def accept_demo(demo_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher accepts a demo request - auto-creates demo class and notifies student"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Teacher not approved")

    demo = await db.demo_requests.find_one({"demo_id": demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo request not found")
    if demo["status"] != "pending":
        raise HTTPException(status_code=400, detail="Demo already processed")

    class_id, student_id, temp_password = await _create_demo_class(demo, user.user_id, user.name)

    # Update demo request
    await db.demo_requests.update_one(
        {"demo_id": demo_id},
        {"$set": {
            "status": "accepted",
            "accepted_by_teacher_id": user.user_id,
            "accepted_by_teacher_name": user.name,
            "student_user_id": student_id,
            "class_id": class_id,
            "accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Log history
    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_accepted",
        "actor_id": user.user_id,
        "actor_name": user.name,
        "actor_role": "teacher",
        "target_type": "demo",
        "target_id": demo_id,
        "related_student_id": student_id,
        "related_student_name": demo["name"],
        "related_class_id": class_id,
        "details": f"{user.name} accepted demo for {demo['name']}. Class scheduled: {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    result = {
        "message": f"Demo accepted! Class created for {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}",
        "class_id": class_id,
        "student_id": student_id
    }
    if temp_password:
        result["student_credentials"] = {"email": demo["email"], "temp_password": temp_password}
    return result


@api_router.post("/demo/assign")
async def assign_demo_to_teacher(data: DemoAssign, request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor assigns a demo to a specific teacher - auto-creates class"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    demo = await db.demo_requests.find_one({"demo_id": data.demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo request not found")
    if demo["status"] != "pending":
        raise HTTPException(status_code=400, detail="Demo already processed")

    teacher = await db.users.find_one({"user_id": data.teacher_id, "role": "teacher"}, {"_id": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    class_id, student_id, temp_password = await _create_demo_class(demo, teacher["user_id"], teacher["name"])

    # Update demo request
    await db.demo_requests.update_one(
        {"demo_id": data.demo_id},
        {"$set": {
            "status": "accepted",
            "accepted_by_teacher_id": teacher["user_id"],
            "accepted_by_teacher_name": teacher["name"],
            "assigned_by": user.user_id,
            "assigned_teacher_id": teacher["user_id"],
            "assigned_teacher_name": teacher["name"],
            "student_user_id": student_id,
            "class_id": class_id,
            "accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Notify teacher
    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": teacher["user_id"],
        "type": "demo_assigned",
        "title": "Demo Session Assigned",
        "message": f"Demo with {demo['name']} assigned to you by {user.name}. Class: {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}",
        "read": False,
        "related_id": class_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Log history
    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_assigned",
        "actor_id": user.user_id,
        "actor_name": user.name,
        "actor_role": user.role,
        "target_type": "demo",
        "target_id": data.demo_id,
        "related_teacher_id": teacher["user_id"],
        "related_teacher_name": teacher["name"],
        "related_student_id": student_id,
        "related_student_name": demo["name"],
        "related_class_id": class_id,
        "details": f"{user.name} assigned demo for {demo['name']} to {teacher['name']}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": f"Demo assigned to {teacher['name']} and class created"}


@api_router.get("/demo/my-demos")
async def get_my_demos(request: Request, authorization: Optional[str] = Header(None)):
    """Get demos relevant to the current user"""
    user = await get_current_user(request, authorization)

    if user.role == "teacher":
        demos = await db.demo_requests.find(
            {"$or": [
                {"accepted_by_teacher_id": user.user_id},
                {"assigned_teacher_id": user.user_id}
            ]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
    elif user.role == "student":
        demos = await db.demo_requests.find(
            {"$or": [
                {"student_user_id": user.user_id},
                {"email": user.email}
            ]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
    else:
        demos = await db.demo_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

    return demos


@api_router.get("/demo/all")
async def get_all_demos(request: Request, authorization: Optional[str] = Header(None)):
    """Get all demo requests - Admin/Counsellor only"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    demos = await db.demo_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return demos


# ==================== DEMO FEEDBACK ENDPOINTS ====================

@api_router.post("/demo/feedback")
async def submit_demo_feedback(feedback: DemoFeedbackCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Student submits feedback after a demo session"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    demo = await db.demo_requests.find_one({"demo_id": feedback.demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")
    if demo.get("student_user_id") != user.user_id and demo.get("email") != user.email:
        raise HTTPException(status_code=403, detail="Not your demo")

    existing = await db.demo_feedback.find_one({"demo_id": feedback.demo_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted")

    feedback_id = f"dfb_{uuid.uuid4().hex[:12]}"
    feedback_doc = {
        "feedback_id": feedback_id,
        "demo_id": feedback.demo_id,
        "student_id": user.user_id,
        "student_name": user.name,
        "teacher_id": demo.get("accepted_by_teacher_id"),
        "teacher_name": demo.get("accepted_by_teacher_name"),
        "rating": feedback.rating,
        "feedback_text": feedback.feedback_text,
        "preferred_teacher_id": feedback.preferred_teacher_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_fb = feedback_doc.copy()
    await db.demo_feedback.insert_one(insert_fb)

    # Update demo request status
    await db.demo_requests.update_one(
        {"demo_id": feedback.demo_id},
        {"$set": {"status": "feedback_submitted", "feedback_id": feedback_id}}
    )

    # Notify counsellors about feedback for allocation
    counsellors = await db.users.find({"role": "counsellor"}, {"_id": 0}).to_list(100)
    for c in counsellors:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": c["user_id"],
            "type": "demo_feedback",
            "title": "Demo Feedback Received",
            "message": f"{user.name} submitted feedback for demo with {demo.get('accepted_by_teacher_name', 'teacher')}. Ready for regular class allocation.",
            "read": False,
            "related_id": feedback.demo_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    # Log history
    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_feedback_submitted",
        "actor_id": user.user_id,
        "actor_name": user.name,
        "actor_role": "student",
        "target_type": "demo",
        "target_id": feedback.demo_id,
        "related_teacher_id": demo.get("accepted_by_teacher_id"),
        "related_teacher_name": demo.get("accepted_by_teacher_name"),
        "related_student_id": user.user_id,
        "related_student_name": user.name,
        "details": f"{user.name} rated demo {feedback.rating}/5. Preferred teacher: {feedback.preferred_teacher_id or 'Any'}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Feedback submitted! A counsellor will assign you to a regular teacher soon."}


@api_router.get("/demo/feedback-pending")
async def get_pending_demo_feedback(request: Request, authorization: Optional[str] = Header(None)):
    """Get demo feedback pending counsellor action"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    feedbacks = await db.demo_feedback.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    return feedbacks


# ==================== DEMO LIMITS ENDPOINTS ====================

@api_router.post("/admin/grant-demo-extra")
async def grant_demo_extra(data: DemoExtraGrant, request: Request, authorization: Optional[str] = Header(None)):
    """Admin grants exactly 1 extra demo chance to a student"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    existing = await db.demo_extras.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Extra demo already granted for this email")

    await db.demo_extras.insert_one({
        "email": data.email,
        "extra_count": 1,
        "granted_by": user.user_id,
        "granted_at": datetime.now(timezone.utc).isoformat()
    })

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_extra_granted",
        "actor_id": user.user_id,
        "actor_name": user.name,
        "actor_role": "admin",
        "target_type": "student",
        "target_id": data.email,
        "details": f"Admin granted 1 extra demo to {data.email}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": f"Extra demo granted to {data.email}"}


# ==================== HISTORY & SEARCH ENDPOINTS ====================

@api_router.get("/history/search")
async def search_history(q: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    """Search comprehensive history - Admin/Counsellor only"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    query = {}
    if q:
        query = {"$or": [
            {"actor_name": {"$regex": q, "$options": "i"}},
            {"actor_email": {"$regex": q, "$options": "i"}},
            {"related_student_name": {"$regex": q, "$options": "i"}},
            {"related_teacher_name": {"$regex": q, "$options": "i"}},
            {"details": {"$regex": q, "$options": "i"}},
            {"action": {"$regex": q, "$options": "i"}}
        ]}

    logs = await db.history_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return logs


@api_router.get("/history/student/{student_id}")
async def get_student_history(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get complete history for a student"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    student = await db.users.find_one({"user_id": student_id}, {"_id": 0, "password_hash": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    demos = await db.demo_requests.find(
        {"$or": [{"student_user_id": student_id}, {"email": student.get("email", "")}]},
        {"_id": 0}
    ).to_list(100)

    assignments = await db.student_teacher_assignments.find(
        {"student_id": student_id}, {"_id": 0}
    ).to_list(100)

    classes = await db.class_sessions.find(
        {"enrolled_students.user_id": student_id}, {"_id": 0}
    ).to_list(100)

    complaints = await db.complaints.find(
        {"student_id": student_id}, {"_id": 0}
    ).to_list(100)

    feedbacks = await db.demo_feedback.find(
        {"student_id": student_id}, {"_id": 0}
    ).to_list(100)

    logs = await db.history_logs.find(
        {"$or": [{"related_student_id": student_id}, {"actor_id": student_id}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    return {
        "student": student,
        "demos": demos,
        "assignments": assignments,
        "classes": classes,
        "complaints": complaints,
        "feedbacks": feedbacks,
        "logs": logs
    }


@api_router.get("/history/teacher/{teacher_id}")
async def get_teacher_history(teacher_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get complete history for a teacher"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    teacher = await db.users.find_one({"user_id": teacher_id}, {"_id": 0, "password_hash": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    demos = await db.demo_requests.find(
        {"accepted_by_teacher_id": teacher_id}, {"_id": 0}
    ).to_list(100)

    assignments = await db.student_teacher_assignments.find(
        {"teacher_id": teacher_id}, {"_id": 0}
    ).to_list(100)

    classes = await db.class_sessions.find(
        {"teacher_id": teacher_id}, {"_id": 0}
    ).to_list(100)

    logs = await db.history_logs.find(
        {"$or": [{"related_teacher_id": teacher_id}, {"actor_id": teacher_id}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    return {
        "teacher": teacher,
        "demos": demos,
        "assignments": assignments,
        "classes": classes,
        "logs": logs
    }


@api_router.get("/history/users")
async def get_all_users_for_history(request: Request, authorization: Optional[str] = Header(None)):
    """Get all users for history search dropdown"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    students = await db.users.find(
        {"role": "student"}, {"_id": 0, "password_hash": 0}
    ).to_list(1000)
    teachers = await db.users.find(
        {"role": "teacher"}, {"_id": 0, "password_hash": 0}
    ).to_list(1000)

    return {"students": students, "teachers": teachers}


# ==================== ADMIN PROOF REVIEW ENDPOINTS ====================

@api_router.get("/admin/approved-proofs")
async def get_admin_pending_proofs(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    request: Request = None,
    authorization: Optional[str] = Header(None)
):
    """Get proofs approved by counsellor, pending admin approval. Filterable by date."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    query = {"status": "verified", "admin_status": "pending"}
    if date_from:
        query["submitted_at"] = query.get("submitted_at", {})
        query["submitted_at"]["$gte"] = date_from
    if date_to:
        if "submitted_at" not in query:
            query["submitted_at"] = {}
        query["submitted_at"]["$lte"] = date_to + "T23:59:59"

    proofs = await db.class_proofs.find(query, {"_id": 0}).sort("submitted_at", -1).to_list(500)

    # Enrich with class and student details
    for proof in proofs:
        cls = await db.class_sessions.find_one({"class_id": proof.get("class_id")}, {"_id": 0})
        if cls:
            proof["class_details"] = {
                "title": cls.get("title"),
                "subject": cls.get("subject"),
                "date": cls.get("date"),
                "end_date": cls.get("end_date"),
                "is_demo": cls.get("is_demo", False),
                "start_time": cls.get("start_time"),
                "end_time": cls.get("end_time"),
                "enrolled_students": cls.get("enrolled_students", [])
            }
        student = await db.users.find_one({"user_id": proof.get("student_id")}, {"_id": 0, "password_hash": 0})
        if student:
            proof["student_details"] = {"name": student.get("name"), "email": student.get("email"), "grade": student.get("grade")}
        teacher = await db.users.find_one({"user_id": proof.get("teacher_id")}, {"_id": 0, "password_hash": 0})
        if teacher:
            proof["teacher_details"] = {"name": teacher.get("name"), "email": teacher.get("email"), "teacher_code": teacher.get("teacher_code")}

    return proofs


@api_router.post("/admin/approve-proof")
async def admin_approve_proof(data: AdminProofApproval, request: Request, authorization: Optional[str] = Header(None)):
    """Admin final approval on proof - auto-credits teacher wallet"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    proof = await db.class_proofs.find_one({"proof_id": data.proof_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof.get("admin_status") != "pending":
        raise HTTPException(status_code=400, detail="Proof not pending admin approval")

    new_status = "approved" if data.approved else "rejected"
    await db.class_proofs.update_one(
        {"proof_id": data.proof_id},
        {"$set": {
            "admin_status": new_status,
            "admin_reviewed_by": user.user_id,
            "admin_reviewed_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": data.admin_notes
        }}
    )

    # If approved, auto-credit teacher wallet
    if data.approved:
        pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
        if pricing:
            cls = await db.class_sessions.find_one({"class_id": proof['class_id']}, {"_id": 0})
            earning = pricing.get('demo_earning_teacher', 0) if cls and cls.get('is_demo') else pricing.get('class_earning_teacher', 0)

            if earning > 0:
                await db.users.update_one(
                    {"user_id": proof['teacher_id']},
                    {"$inc": {"credits": earning}}
                )
                await db.transactions.insert_one({
                    "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                    "user_id": proof['teacher_id'],
                    "type": "earning",
                    "amount": earning,
                    "description": f"Admin approved: {proof.get('class_title', 'Class')}",
                    "proof_id": data.proof_id,
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                # Notify teacher about credit
                await db.notifications.insert_one({
                    "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                    "user_id": proof['teacher_id'],
                    "type": "credit_earned",
                    "title": "Credits Earned!",
                    "message": f"{earning} credits added to your wallet for '{proof.get('class_title', 'Class')}'.",
                    "read": False,
                    "related_id": data.proof_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

    action = "approved & teacher credited" if data.approved else "rejected"
    return {"message": f"Proof {action} by admin"}


# ==================== SEARCH & FILTER ENDPOINTS ====================

@api_router.get("/search/teachers")
async def search_teachers(q: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    """Search teachers by name or teacher_code"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    if not q.strip():
        teachers = await db.users.find(
            {"role": "teacher"},
            {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)
    else:
        teachers = await db.users.find(
            {"role": "teacher", "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"teacher_code": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}}
            ]},
            {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)

    return teachers


@api_router.get("/filter/classes")
async def filter_classes(
    grade: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    is_demo: Optional[str] = None,
    status: Optional[str] = None,
    teacher_id: Optional[str] = None,
    search: Optional[str] = None,
    request: Request = None,
    authorization: Optional[str] = Header(None)
):
    """Filter classes by grade, location, type, status. Admin/Counsellor only."""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    query = {}
    if is_demo is not None:
        query["is_demo"] = is_demo.lower() == "true"
    if status:
        query["status"] = status
    if teacher_id:
        query["teacher_id"] = teacher_id
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"class_id": {"$regex": search, "$options": "i"}},
            {"subject": {"$regex": search, "$options": "i"}},
            {"teacher_name": {"$regex": search, "$options": "i"}}
        ]

    classes = await db.class_sessions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # Filter by student location/grade if specified
    if grade or city or state:
        student_query = {"role": "student"}
        if grade:
            student_query["grade"] = grade
        if city:
            student_query["city"] = {"$regex": city, "$options": "i"}
        if state:
            student_query["state"] = {"$regex": state, "$options": "i"}
        matching_students = await db.users.find(student_query, {"_id": 0}).to_list(10000)
        matching_ids = set(s["user_id"] for s in matching_students)
        classes = [c for c in classes if any(e["user_id"] in matching_ids for e in c.get("enrolled_students", []))]

    return classes


@api_router.get("/filter/students")
async def filter_students(
    grade: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    request: Request = None,
    authorization: Optional[str] = Header(None)
):
    """Filter students by location, grade, search. Teacher/Counsellor/Admin."""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor", "teacher"]:
        raise HTTPException(status_code=403, detail="Access denied")

    query = {"role": "student"}
    if grade:
        query["grade"] = grade
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if state:
        query["state"] = {"$regex": state, "$options": "i"}
    if country:
        query["country"] = {"$regex": country, "$options": "i"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"institute": {"$regex": search, "$options": "i"}}
        ]

    students = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(1000)
    return students


# ==================== WALLET ENDPOINTS ====================

@api_router.get("/wallet/summary")
async def get_wallet_summary(request: Request, authorization: Optional[str] = Header(None)):
    """Get wallet balance and transaction history"""
    user = await get_current_user(request, authorization)

    transactions = await db.transactions.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    # Get pending earnings (proofs pending admin approval)
    pending_earnings = 0
    if user.role == "teacher":
        pending_proofs = await db.class_proofs.find(
            {"teacher_id": user.user_id, "status": "verified", "admin_status": "pending"},
            {"_id": 0}
        ).to_list(100)
        pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
        if pricing:
            for p in pending_proofs:
                cls = await db.class_sessions.find_one({"class_id": p.get("class_id")}, {"_id": 0})
                if cls and cls.get("is_demo"):
                    pending_earnings += pricing.get("demo_earning_teacher", 0)
                else:
                    pending_earnings += pricing.get("class_earning_teacher", 0)

    return {
        "balance": user.credits,
        "pending_earnings": pending_earnings,
        "bank_details": getattr(user, "bank_details", None),
        "transactions": transactions
    }


# ==================== TEACHER FEEDBACK TO STUDENT ====================

@api_router.post("/teacher/feedback-to-student")
async def teacher_feedback_to_student(data: TeacherFeedbackToStudent, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher sends performance feedback to student (in-app notification)"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    student = await db.users.find_one({"user_id": data.student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    feedback_id = f"tfb_{uuid.uuid4().hex[:12]}"
    feedback_doc = {
        "feedback_id": feedback_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "student_id": data.student_id,
        "student_name": student["name"],
        "class_id": data.class_id,
        "feedback_text": data.feedback_text,
        "performance_rating": data.performance_rating,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_fb = feedback_doc.copy()
    await db.teacher_student_feedback.insert_one(insert_fb)

    # In-app notification to student
    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": data.student_id,
        "type": "teacher_feedback",
        "title": f"Feedback from {user.name}",
        "message": f"Performance: {data.performance_rating.replace('_', ' ').title()}. {data.feedback_text}",
        "read": False,
        "related_id": feedback_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Email notification to student
    await send_email(
        student["email"],
        f"Performance Feedback from {user.name} - Kaimera Learning",
        f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#0ea5e9,#8b5cf6);padding:30px;border-radius:16px;color:#fff;text-align:center;">
            <h1 style="margin:0;font-size:24px;">Teacher Feedback</h1>
        </div>
        <div style="padding:20px;background:#f8fafc;border-radius:0 0 16px 16px;">
            <p>Hi <strong>{student['name']}</strong>,</p>
            <p>Your teacher <strong>{user.name}</strong> has shared feedback about your performance:</p>
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:16px 0;">
                <p style="color:#0ea5e9;font-weight:bold;margin:0 0 8px;">Rating: {data.performance_rating.replace('_', ' ').title()}</p>
                <p style="margin:0;color:#334155;">{data.feedback_text}</p>
            </div>
            <p style="color:#64748b;font-size:14px;">Keep up the great work! Log in to your dashboard for more details.</p>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:16px;">Kaimera Learning</p>
        </div>"""
    )

    return {"message": "Feedback sent to student"}


# ==================== BADGE SYSTEM ====================

@api_router.post("/admin/assign-badge")
async def assign_badge(data: BadgeAssign, request: Request, authorization: Optional[str] = Header(None)):
    """Admin assigns a badge to a teacher or counsellor"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    target = await db.users.find_one({"user_id": data.user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] not in ["teacher", "counsellor"]:
        raise HTTPException(status_code=400, detail="Badges can only be assigned to teachers or counsellors")

    await db.users.update_one(
        {"user_id": data.user_id},
        {"$addToSet": {"badges": data.badge_name}}
    )

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": data.user_id,
        "type": "badge_assigned",
        "title": "New Badge Earned!",
        "message": f"You've been awarded the '{data.badge_name}' badge by admin.",
        "read": False,
        "related_id": data.badge_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": f"Badge '{data.badge_name}' assigned to {target['name']}"}


@api_router.delete("/admin/remove-badge")
async def remove_badge(user_id: str, badge_name: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin removes a badge from a user"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"badges": badge_name}}
    )

    return {"message": f"Badge '{badge_name}' removed"}


# ==================== RENEWAL CHECK ====================

@api_router.get("/renewal/check")
async def check_renewals(request: Request, authorization: Optional[str] = Header(None)):
    """Check for classes nearing 80% completion - triggers renewal alerts"""
    user = await get_current_user(request, authorization)

    query = {"status": {"$in": ["scheduled", "in_progress"]}}
    if user.role == "teacher":
        query["teacher_id"] = user.user_id
    elif user.role == "student":
        query["enrolled_students.user_id"] = user.user_id
    elif user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Access denied")

    classes = await db.class_sessions.find(query, {"_id": 0}).to_list(1000)
    renewal_needed = []

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for cls in classes:
        try:
            start = datetime.strptime(cls.get("date", today_str), "%Y-%m-%d")
            end = datetime.strptime(cls.get("end_date", cls.get("date", today_str)), "%Y-%m-%d")
            total_days = max((end - start).days, 1)
            today_dt = datetime.strptime(today_str, "%Y-%m-%d")
            elapsed = max((today_dt - start).days, 0)
            pct = (elapsed / total_days) * 100 if total_days > 0 else 0
            remaining_pct = 100 - pct
            if pct >= 80 and remaining_pct > 0:
                cls["completion_pct"] = round(pct, 1)
                cls["remaining_pct"] = round(remaining_pct, 1)
                cls["days_remaining"] = max((end - today_dt).days, 0)
                renewal_needed.append(cls)
        except Exception:
            pass

    return renewal_needed


@api_router.post("/renewal/schedule-meeting")
async def schedule_renewal_meeting(class_id: str, meeting_date: str, request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor/Teacher schedules a renewal meeting with student"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    meeting_id = f"meet_{uuid.uuid4().hex[:12]}"
    student_ids = [s["user_id"] for s in cls.get("enrolled_students", [])]

    meeting_doc = {
        "meeting_id": meeting_id,
        "class_id": class_id,
        "class_title": cls.get("title", ""),
        "teacher_id": cls.get("teacher_id"),
        "teacher_name": cls.get("teacher_name"),
        "student_ids": student_ids,
        "scheduled_by": user.user_id,
        "scheduled_by_name": user.name,
        "meeting_date": meeting_date,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_meeting = meeting_doc.copy()
    await db.renewal_meetings.insert_one(insert_meeting)

    # Notify students
    for sid in student_ids:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": sid,
            "type": "renewal_meeting",
            "title": "Renewal Meeting Scheduled",
            "message": f"A renewal meeting for '{cls.get('title', '')}' has been scheduled for {meeting_date} by {user.name}.",
            "read": False,
            "related_id": meeting_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {"message": "Renewal meeting scheduled", "meeting_id": meeting_id}


@api_router.get("/renewal/my-meetings")
async def get_my_renewal_meetings(request: Request, authorization: Optional[str] = Header(None)):
    """Get renewal meetings for current user"""
    user = await get_current_user(request, authorization)

    if user.role == "student":
        meetings = await db.renewal_meetings.find(
            {"student_ids": user.user_id},
            {"_id": 0}
        ).sort("meeting_date", -1).to_list(100)
    elif user.role == "teacher":
        meetings = await db.renewal_meetings.find(
            {"teacher_id": user.user_id},
            {"_id": 0}
        ).sort("meeting_date", -1).to_list(100)
    else:
        meetings = await db.renewal_meetings.find({}, {"_id": 0}).sort("meeting_date", -1).to_list(100)

    return meetings


# ==================== LEARNING KIT ENDPOINTS ====================

@api_router.post("/admin/learning-kit/upload")
async def upload_learning_kit(
    title: str = Form(...),
    grade: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    request: Request = None,
    authorization: Optional[str] = Header(None)
):
    """Admin uploads a learning kit file (PDF/doc) for a specific grade"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    allowed_types = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.jpg', '.png']
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Allowed: {', '.join(allowed_types)}")

    kit_id = f"kit_{uuid.uuid4().hex[:12]}"
    safe_filename = f"{kit_id}{ext}"
    file_path = UPLOADS_DIR / safe_filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    kit_doc = {
        "kit_id": kit_id,
        "title": title,
        "grade": grade,
        "description": description,
        "file_name": file.filename,
        "stored_name": safe_filename,
        "file_type": ext,
        "file_size": len(content),
        "uploaded_by": user.user_id,
        "uploaded_by_name": user.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_doc = kit_doc.copy()
    await db.learning_kits.insert_one(insert_doc)

    return {"message": f"Learning kit '{title}' uploaded for Grade {grade}", "kit_id": kit_id}


@api_router.get("/learning-kit")
async def list_learning_kits(grade: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
    """Get learning kits, optionally filtered by grade"""
    user = await get_current_user(request, authorization)

    query = {}
    if grade:
        query["grade"] = grade
    elif user.role == "student":
        query["grade"] = getattr(user, "grade", None) or ""

    kits = await db.learning_kits.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return kits


@api_router.get("/learning-kit/download/{kit_id}")
async def download_learning_kit(kit_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Download a learning kit file"""
    user = await get_current_user(request, authorization)

    kit = await db.learning_kits.find_one({"kit_id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit not found")

    file_path = UPLOADS_DIR / kit["stored_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=str(file_path),
        filename=kit["file_name"],
        media_type="application/octet-stream"
    )


@api_router.delete("/admin/learning-kit/{kit_id}")
async def delete_learning_kit(kit_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin deletes a learning kit"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    kit = await db.learning_kits.find_one({"kit_id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit not found")

    file_path = UPLOADS_DIR / kit["stored_name"]
    if file_path.exists():
        file_path.unlink()

    await db.learning_kits.delete_one({"kit_id": kit_id})
    return {"message": "Learning kit deleted"}


@api_router.get("/learning-kit/grades")
async def get_available_grades(request: Request, authorization: Optional[str] = Header(None)):
    """Get all grades that have learning kits"""
    user = await get_current_user(request, authorization)
    grades = await db.learning_kits.distinct("grade")
    return sorted(grades)


# ==================== TEACHER CALENDAR ENDPOINTS ====================

@api_router.post("/teacher/calendar")
async def add_calendar_entry(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher adds a content plan entry to their calendar"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    body = await request.json()
    entry_id = f"cal_{uuid.uuid4().hex[:12]}"
    entry_doc = {
        "entry_id": entry_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "date": body.get("date"),
        "title": body.get("title", ""),
        "description": body.get("description", ""),
        "subject": body.get("subject", ""),
        "color": body.get("color", "#0ea5e9"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_entry = entry_doc.copy()
    await db.teacher_calendar.insert_one(insert_entry)
    return {"message": "Calendar entry added", "entry_id": entry_id}


@api_router.get("/teacher/calendar")
async def get_calendar_entries(month: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
    """Get teacher's calendar entries, optionally by month (YYYY-MM)"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    query = {"teacher_id": user.user_id}
    if month:
        query["date"] = {"$regex": f"^{month}"}

    entries = await db.teacher_calendar.find(query, {"_id": 0}).sort("date", 1).to_list(500)
    return entries


@api_router.delete("/teacher/calendar/{entry_id}")
async def delete_calendar_entry(entry_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher removes a calendar entry"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    result = await db.teacher_calendar.delete_one({"entry_id": entry_id, "teacher_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Calendar entry deleted"}


# ==================== NAG SCREEN CHECK ====================

@api_router.get("/student/nag-check")
async def student_nag_check(request: Request, authorization: Optional[str] = Header(None)):
    """Check if student needs nag screen (unassigned to regular teacher)"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    # Check for any active/approved assignment
    active_assignment = await db.student_teacher_assignments.find_one(
        {"student_id": user.user_id, "status": "approved"},
        {"_id": 0}
    )

    # Check for any upcoming regular classes
    regular_classes = await db.class_sessions.find(
        {"enrolled_students.user_id": user.user_id, "is_demo": {"$ne": True}, "status": {"$in": ["scheduled", "in_progress"]}},
        {"_id": 0}
    ).to_list(10)

    # Check demo count
    demo_count = await db.demo_requests.count_documents(
        {"$or": [{"student_user_id": user.user_id}, {"email": user.email}]}
    )

    show_nag = not active_assignment and len(regular_classes) == 0
    return {
        "show_nag": show_nag,
        "has_assignment": active_assignment is not None,
        "regular_class_count": len(regular_classes),
        "demo_count": demo_count
    }


# ==================== ADMIN CREDENTIAL MANAGEMENT ====================

@api_router.post("/admin/reset-password")
async def admin_reset_password(request: Request, authorization: Optional[str] = Header(None)):
    """Admin resets password for any user"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    body = await request.json()
    target_email = body.get("email")
    new_password = body.get("new_password")
    if not target_email or not new_password:
        raise HTTPException(status_code=400, detail="Email and new_password required")

    target = await db.users.find_one({"email": target_email}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    password_hash = hash_password(new_password)
    await db.users.update_one({"email": target_email}, {"$set": {"password_hash": password_hash}})

    return {"message": f"Password reset for {target['name']} ({target_email})", "role": target["role"]}


@api_router.get("/admin/all-users")
async def admin_get_all_users(request: Request, authorization: Optional[str] = Header(None)):
    """Admin gets all users with search capability"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    users_list = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(5000)
    return users_list


@api_router.get("/admin/user-detail/{user_id}")
async def admin_get_user_detail(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin gets full detail of any user with all related data"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    target = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    result = {"user": target}

    if target["role"] == "student":
        result["assignments"] = await db.student_teacher_assignments.find({"student_id": user_id}, {"_id": 0}).to_list(100)
        result["classes"] = await db.class_sessions.find({"enrolled_students.user_id": user_id}, {"_id": 0}).to_list(100)
        result["demos"] = await db.demo_requests.find({"$or": [{"student_user_id": user_id}, {"email": target.get("email")}]}, {"_id": 0}).to_list(100)
        result["complaints"] = await db.complaints.find({"student_id": user_id}, {"_id": 0}).to_list(100)
    elif target["role"] == "teacher":
        result["assignments"] = await db.student_teacher_assignments.find({"teacher_id": user_id}, {"_id": 0}).to_list(100)
        result["classes"] = await db.class_sessions.find({"teacher_id": user_id}, {"_id": 0}).to_list(100)
        result["demos"] = await db.demo_requests.find({"accepted_by_teacher_id": user_id}, {"_id": 0}).to_list(100)
    elif target["role"] == "counsellor":
        result["assignments"] = await db.student_teacher_assignments.find({"assigned_by": user_id}, {"_id": 0}).to_list(500)
        result["history_logs"] = await db.history_logs.find({"actor_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)

    result["transactions"] = await db.transactions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return result


# ==================== BADGE TEMPLATE ENDPOINTS ====================

@api_router.post("/admin/badge-template")
async def create_badge_template(request: Request, authorization: Optional[str] = Header(None)):
    """Admin creates a badge template"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Badge name required")

    existing = await db.badge_templates.find_one({"name": name}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Badge already exists")

    await db.badge_templates.insert_one({
        "badge_id": f"badge_{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": body.get("description", ""),
        "color": body.get("color", "#8b5cf6"),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"message": f"Badge '{name}' created"}


@api_router.get("/admin/badge-templates")
async def get_badge_templates(request: Request, authorization: Optional[str] = Header(None)):
    """Get all badge templates"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    templates = await db.badge_templates.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return templates


@api_router.delete("/admin/badge-template/{badge_id}")
async def delete_badge_template(badge_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin deletes a badge template"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    await db.badge_templates.delete_one({"badge_id": badge_id})
    return {"message": "Badge template deleted"}


# ==================== TEACHER GROUPED CLASSES ====================

@api_router.get("/teacher/grouped-classes")
async def get_teacher_grouped_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher's classes grouped by student, with today's classes separate"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    all_classes = await db.class_sessions.find(
        {"teacher_id": user.user_id},
        {"_id": 0}
    ).sort("date", -1).to_list(1000)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    today_classes = []
    active_by_student = {}
    ended_classes = []

    for cls in all_classes:
        start_date = cls.get("date", "")
        end_date = cls.get("end_date", start_date)

        # Determine if class is truly ended
        if end_date < today_str and cls.get("status") not in ["in_progress"]:
            cls["display_status"] = "ended"
            ended_classes.append(cls)
            continue

        # Today's classes
        if start_date <= today_str <= end_date:
            cls["is_today"] = True
            today_classes.append(cls)

        # Group by student
        for student in cls.get("enrolled_students", []):
            sid = student.get("user_id", "unknown")
            sname = student.get("name", "Unknown Student")
            if sid not in active_by_student:
                active_by_student[sid] = {"student_id": sid, "student_name": sname, "classes": []}
            active_by_student[sid]["classes"].append(cls)

    # Get student details for active students
    for sid in active_by_student:
        student = await db.users.find_one({"user_id": sid}, {"_id": 0, "password_hash": 0})
        if student:
            active_by_student[sid]["student_details"] = student

    return {
        "today": today_classes,
        "by_student": list(active_by_student.values()),
        "ended_count": len(ended_classes)
    }


# ==================== COUNSELLOR STUDENT SEARCH ====================

@api_router.get("/counsellor/search-students")
async def counsellor_search_students(q: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    """Search students by name, email, or student_code"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if q.strip():
        students = await db.users.find(
            {"role": "student", "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}},
                {"student_code": {"$regex": q, "$options": "i"}}
            ]},
            {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)
    else:
        students = await db.users.find(
            {"role": "student"},
            {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)

    return students


# ==================== TEACHER SCHEDULE VIEW ====================

@api_router.get("/teacher/schedule")
async def get_teacher_schedule(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher's full schedule for schedule planner view"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    classes = await db.class_sessions.find(
        {"teacher_id": user.user_id, "status": {"$in": ["scheduled", "in_progress"]}},
        {"_id": 0}
    ).sort("date", 1).to_list(500)

    return classes


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
    # Backfill teacher_code for existing teachers without one
    teachers_without_code = await db.users.find(
        {"role": "teacher", "$or": [{"teacher_code": None}, {"teacher_code": {"$exists": False}}]},
        {"_id": 0}
    ).to_list(1000)
    for t in teachers_without_code:
        code = await generate_teacher_code()
        await db.users.update_one({"user_id": t["user_id"]}, {"$set": {"teacher_code": code}})
        logger.info(f"Backfilled teacher_code {code} for {t['name']}")
    # Backfill student_code for existing students without one
    students_without_code = await db.users.find(
        {"role": "student", "$or": [{"student_code": None}, {"student_code": {"$exists": False}}]},
        {"_id": 0}
    ).to_list(5000)
    for s in students_without_code:
        code = await generate_student_code()
        await db.users.update_one({"user_id": s["user_id"]}, {"$set": {"student_code": code}})
        logger.info(f"Backfilled student_code {code} for {s.get('name', s['email'])}")
    logger.info("Kaimera Learning API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
