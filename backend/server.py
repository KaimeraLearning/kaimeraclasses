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
    role: str  # student, teacher, admin, counsellor
    credits: float = 0.0
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_approved: bool = True  # For teacher approval
    phone: Optional[str] = None  # Only for students and counsellors, NOT teachers
    bio: Optional[str] = None  # Teacher profile bio
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
    credit_price: float

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
        "classes": classes,
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
        {" class_id": class_id},
        {"$set": {"status": "in_progress"}}
    )
    
    return {"message": "Class started"}

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
        "credit_price": assignment.credit_price,
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
    
    teacher_doc = {
        "user_id": user_id,
        "email": teacher_data.email,
        "name": teacher_data.name,
        "role": "teacher",
        "credits": 0.0,  # Teacher starts with 0, earns through classes
        "picture": None,
        "password_hash": password_hash,
        "is_approved": True,  # Admin-created teachers are auto-approved
        "phone": None,  # Teachers cannot add phone
        "bio": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(teacher_doc)
    
    return {"message": "Teacher account created successfully", "user_id": user_id, "email": teacher_data.email}

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
    """Counsellor verifies a class proof"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    
    proof = await db.class_proofs.find_one({"proof_id": verification.proof_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof['status'] != "pending":
        raise HTTPException(status_code=400, detail="Proof already processed")
    
    new_status = "verified" if verification.approved else "rejected"
    
    await db.class_proofs.update_one(
        {"proof_id": verification.proof_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": user.user_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_notes": verification.reviewer_notes
        }}
    )
    
    # Update class verification status
    await db.class_sessions.update_one(
        {"class_id": proof['class_id']},
        {"$set": {"verification_status": new_status}}
    )
    
    # If approved, add credits to teacher's wallet
    if verification.approved:
        pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
        if pricing:
            cls = await db.class_sessions.find_one({"class_id": proof['class_id']}, {"_id": 0})
            if cls and cls.get('is_demo'):
                earning = pricing.get('demo_earning_teacher', 0)
            else:
                earning = pricing.get('class_earning_teacher', 0)
            
            if earning > 0:
                await db.users.update_one(
                    {"user_id": proof['teacher_id']},
                    {"$inc": {"credits": earning}}
                )
                
                txn_id = f"txn_{uuid.uuid4().hex[:12]}"
                await db.transactions.insert_one({
                    "transaction_id": txn_id,
                    "user_id": proof['teacher_id'],
                    "type": "earning",
                    "amount": earning,
                    "description": f"Class verified: {proof['class_title']}",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    
    action = "approved" if verification.approved else "rejected"
    return {"message": f"Proof {action} successfully"}

# ==================== COMPLAINT ENDPOINTS ====================

@api_router.post("/complaints/create")
async def create_complaint(complaint: ComplaintCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Create a new complaint"""
    user = await get_current_user(request, authorization)
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin cannot create complaints")
    
    complaint_id = f"complaint_{uuid.uuid4().hex[:12]}"
    complaint_doc = {
        "complaint_id": complaint_id,
        "raised_by": user.user_id,
        "raised_by_name": user.name,
        "raised_by_role": user.role,
        "subject": complaint.subject,
        "description": complaint.description,
        "related_class_id": complaint.related_class_id,
        "status": "open",
        "resolution": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None
    }
    
    await db.complaints.insert_one(complaint_doc)
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
    """Admin views all complaints"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
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
