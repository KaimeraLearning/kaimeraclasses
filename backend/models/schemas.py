from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str  # student, teacher, admin, counsellor
    credits: float = 0.0
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_approved: bool = True  # For teacher approval
    is_verified: bool = True  # OTP verification for manually created users
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
    learning_plan_id: Optional[str] = None
    class_frequency: Optional[str] = None
    specific_days: Optional[str] = None
    demo_performance_notes: Optional[str] = None
    assigned_days: Optional[int] = None


class LearningPlan(BaseModel):
    plan_id: Optional[str] = None
    name: str
    price: float
    details: str  # Syllabus / description
    max_days: Optional[int] = None  # Max class days allowed for this plan
    is_active: bool = True
    created_at: Optional[str] = None


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


class TeacherDemoFeedback(BaseModel):
    demo_id: str
    student_id: str
    feedback_text: str
    performance_rating: str  # excellent, good, average, needs_improvement
    recommended_frequency: Optional[str] = None


class BadgeAssign(BaseModel):
    user_id: str
    badge_name: str


class AdminProofApproval(BaseModel):
    proof_id: str
    approved: bool
    admin_notes: Optional[str] = None


class ChatMessage(BaseModel):
    recipient_id: str
    message: str


class StudentFeedbackRating(BaseModel):
    class_id: str
    rating: int  # 1-5
    comments: str
