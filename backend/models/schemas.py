"""Pydantic models for request/response validation"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


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


class ClassSessionCreate(BaseModel):
    title: str
    subject: str
    class_type: str
    date: str
    start_time: str
    end_time: str
    max_students: int
    assigned_student_id: str
    duration_days: int
    is_demo: bool = False


class StudentProfileUpdate(BaseModel):
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    phone: Optional[str] = None


class ClassProofSubmit(BaseModel):
    class_id: str
    feedback_text: str
    student_performance: str
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
    status: str


class CreateStudentAccount(BaseModel):
    email: EmailStr
    password: str
    name: str
    institute: Optional[str] = None
    goal: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    phone: Optional[str] = None


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
