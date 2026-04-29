"""Admin routes"""
import os
import uuid
import bcrypt
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Header, Form, UploadFile, File
from typing import Optional

from database import db
from models.schemas import (
    TeacherApproval, CreditAdjustment, AssignStudentToTeacher,
    SystemPricing, CreateTeacherAccount, CreateStudentAccount,
    AdminProofApproval, BadgeAssign, DemoExtraGrant, ComplaintResolve,
    LearningPlan
)
from services.auth import get_current_user, hash_password
from services.helpers import generate_teacher_code, generate_student_code, send_email, generate_otp, insert_admin_mirror_txn, notify_event, generate_temp_password, invalidate_email_config_cache, _get_email_config

router = APIRouter()


def validate_gmail(email: str):
    """Enforce @gmail.com only for manual user creation"""
    if not email.lower().endswith('@gmail.com'):
        raise HTTPException(status_code=400, detail="Only @gmail.com email addresses are allowed")

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/admin/approve-teacher")
async def approve_teacher(approval: TeacherApproval, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    teacher = await db.users.find_one({"user_id": approval.user_id}, {"_id": 0})
    if not teacher or teacher['role'] != "teacher":
        raise HTTPException(status_code=404, detail="Teacher not found")
    await db.users.update_one({"user_id": approval.user_id}, {"$set": {"is_approved": approval.approved}})
    action = "approved" if approval.approved else "rejected"
    return {"message": f"Teacher {action} successfully"}


@router.get("/admin/teachers")
async def get_teachers(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    teachers = await db.users.find({"role": "teacher"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for teacher in teachers:
        if isinstance(teacher['created_at'], str):
            teacher['created_at'] = datetime.fromisoformat(teacher['created_at'])
    return teachers


@router.get("/admin/classes")
async def get_all_classes(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    classes = await db.class_sessions.find({}, {"_id": 0}).to_list(1000)
    for cls in classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    return classes


@router.get("/admin/transactions")
async def get_transactions(request: Request, authorization: Optional[str] = Header(None), role: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None, search: Optional[str] = None, view: Optional[str] = None):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    query = {}
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_q

    if role and role != "all":
        user_ids = [u["user_id"] for u in await db.users.find({"role": role}, {"_id": 0, "user_id": 1}).to_list(5000)]
        query["user_id"] = {"$in": user_ids}

    if search:
        user_ids_search = [u["user_id"] for u in await db.users.find(
            {"$or": [{"name": {"$regex": search, "$options": "i"}}, {"email": {"$regex": search, "$options": "i"}}, {"student_code": {"$regex": search, "$options": "i"}}, {"teacher_code": {"$regex": search, "$options": "i"}}]},
            {"_id": 0, "user_id": 1}
        ).to_list(5000)]
        if "user_id" in query:
            query["user_id"] = {"$in": list(set(query["user_id"]["$in"]) & set(user_ids_search))}
        else:
            query["user_id"] = {"$in": user_ids_search}

    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)

    # Batch fetch all users referenced in transactions (fixes N+1 query)
    unique_user_ids = list(set(txn.get("user_id") for txn in transactions if txn.get("user_id")))
    user_cache = {}
    if unique_user_ids:
        users_batch = await db.users.find(
            {"user_id": {"$in": unique_user_ids}},
            {"_id": 0, "user_id": 1, "name": 1, "role": 1, "student_code": 1, "teacher_code": 1, "email": 1}
        ).to_list(len(unique_user_ids))
        user_cache = {u["user_id"]: u for u in users_batch}

    for txn in transactions:
        uid = txn.get("user_id")
        info = user_cache.get(uid, {})
        txn["user_name"] = info.get("name", "Unknown")
        txn["user_role"] = info.get("role", "")
        txn["user_code"] = info.get("student_code") or info.get("teacher_code") or ""

    # Enrich with reference labels (class title + receipt id) for admin ledger UX
    class_ids = list({t.get("class_id") for t in transactions if t.get("class_id")})
    payment_ids = list({t.get("payment_id") for t in transactions if t.get("payment_id")})
    counter_ids = list({t.get("counterparty_user_id") for t in transactions if t.get("counterparty_user_id")})
    cls_map = {}
    pay_map = {}
    cp_map = {}
    if class_ids:
        for c in await db.class_sessions.find({"class_id": {"$in": class_ids}}, {"_id": 0, "class_id": 1, "title": 1, "date": 1, "teacher_name": 1}).to_list(len(class_ids)):
            cls_map[c["class_id"]] = c
    if payment_ids:
        for p in await db.payments.find({"payment_id": {"$in": payment_ids}}, {"_id": 0, "payment_id": 1, "receipt_id": 1, "razorpay_payment_id": 1, "status": 1}).to_list(len(payment_ids)):
            pay_map[p["payment_id"]] = p
    if counter_ids:
        for u in await db.users.find({"user_id": {"$in": counter_ids}}, {"_id": 0, "user_id": 1, "name": 1, "role": 1}).to_list(len(counter_ids)):
            cp_map[u["user_id"]] = u
    for txn in transactions:
        ref = {}
        if txn.get("class_id") and cls_map.get(txn["class_id"]):
            c = cls_map[txn["class_id"]]
            ref["class_title"] = c.get("title")
            ref["class_date"] = c.get("date")
            ref["teacher_name"] = c.get("teacher_name")
        if txn.get("payment_id") and pay_map.get(txn["payment_id"]):
            p = pay_map[txn["payment_id"]]
            ref["payment_id"] = p["payment_id"]
            ref["receipt_id"] = p.get("receipt_id")
            ref["razorpay_payment_id"] = p.get("razorpay_payment_id")
        if txn.get("counterparty_user_id") and cp_map.get(txn["counterparty_user_id"]):
            cp = cp_map[txn["counterparty_user_id"]]
            ref["counterparty_name"] = cp.get("name")
            ref["counterparty_role"] = cp.get("role")
        txn["reference"] = ref

    if view == "daily":
        daily = defaultdict(lambda: {"date": "", "total_revenue": 0, "total_credits_added": 0, "total_deductions": 0, "count": 0})
        for txn in transactions:
            day = txn.get("created_at", "")[:10]
            if day:
                daily[day]["date"] = day
                daily[day]["count"] += 1
                amt = txn.get("amount", 0)
                if amt > 0:
                    daily[day]["total_credits_added"] += amt
                else:
                    daily[day]["total_deductions"] += abs(amt)
                daily[day]["total_revenue"] += amt
        return sorted(daily.values(), key=lambda x: x["date"], reverse=True)
    return transactions


@router.post("/admin/adjust-credits")
async def adjust_credits(adjustment: CreditAdjustment, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    target_user = await db.users.find_one({"user_id": adjustment.user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if adjustment.action == "add":
        await db.users.update_one({"user_id": adjustment.user_id}, {"$inc": {"credits": adjustment.amount}})
        description = f"Admin added {adjustment.amount} credits"
    else:
        # Prevent negative balance
        if target_user.get("credits", 0) < adjustment.amount:
            raise HTTPException(status_code=400, detail=f"Cannot deduct {adjustment.amount} credits. User only has {target_user.get('credits', 0)} credits.")
        await db.users.update_one({"user_id": adjustment.user_id}, {"$inc": {"credits": -adjustment.amount}})
        description = f"Admin deducted {adjustment.amount} credits"

    txn_type = "credit_add" if adjustment.action == "add" else "credit_deduct"
    txn_amount = adjustment.amount if adjustment.action == "add" else -adjustment.amount
    await db.transactions.insert_one({
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}", "user_id": adjustment.user_id,
        "type": txn_type, "amount": txn_amount, "description": description,
        "counterparty_user_id": user.user_id,
        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
    })
    # Mirror in admin wallet — opposite sign
    # If admin ADDED credits to user: admin paid out → -amount.
    # If admin DEDUCTED credits from user: admin reclaimed → +amount.
    # Skip mirror when admin adjusts admin's own wallet (would double-count).
    if adjustment.user_id != user.user_id:
        await insert_admin_mirror_txn(
            amount=-txn_amount,
            description=(f"Manual credit ADD to {target_user.get('name','user')} (-{adjustment.amount})"
                         if adjustment.action == "add"
                         else f"Manual credit DEDUCT from {target_user.get('name','user')} (+{adjustment.amount})"),
            txn_type="manual_adjustment",
            counterparty_user_id=adjustment.user_id
        )
    return {"message": "Credits adjusted successfully"}


@router.post("/admin/assign-student")
async def assign_student_to_teacher(assignment: AssignStudentToTeacher, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    student = await db.users.find_one({"user_id": assignment.student_id, "role": "student"}, {"_id": 0})
    teacher = await db.users.find_one({"user_id": assignment.teacher_id, "role": "teacher"}, {"_id": 0})
    if not student or not teacher:
        raise HTTPException(status_code=404, detail="Student or teacher not found")

    # DEMO-FIRST CONSTRAINT - check both student_id and student_user_id fields
    demo = await db.demo_requests.find_one({
        "$or": [{"student_id": assignment.student_id}, {"student_user_id": assignment.student_id}],
        "status": {"$in": ["completed", "feedback_submitted"]}
    }, {"_id": 0})
    if not demo:
        # Also check if a completed demo class exists for this student
        demo_class = await db.class_sessions.find_one({
            "assigned_student_id": assignment.student_id, "is_demo": True,
            "status": "completed"
        }, {"_id": 0})
        if not demo_class:
            raise HTTPException(status_code=400, detail="Cannot assign: Student has not completed a demo class yet. A successful demo is required before assignment.")

    if teacher.get("is_suspended"):
        raise HTTPException(status_code=400, detail=f"Teacher {teacher['name']} is currently suspended and cannot accept new students.")

    existing_active = await db.student_teacher_assignments.find_one({"student_id": assignment.student_id, "status": {"$in": ["pending", "approved"]}}, {"_id": 0})
    if existing_active:
        raise HTTPException(status_code=400, detail=f"Student already assigned to {existing_active['teacher_name']}. Only one teacher per student allowed.")

    # PROOF GUARDRAIL: Check if previous class has pending proof
    prev_classes = await db.class_sessions.find(
        {"assigned_student_id": assignment.student_id, "status": "completed", "verification_status": "pending"},
        {"_id": 0, "class_id": 1, "title": 1, "teacher_id": 1}
    ).to_list(100)
    if prev_classes:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign: Proof of completion for the previous session is still pending from the Teacher."
        )

    # Lookup learning plan if provided
    learning_plan = None
    if assignment.learning_plan_id:
        learning_plan = await db.learning_plans.find_one({"plan_id": assignment.learning_plan_id, "is_active": True}, {"_id": 0})
        if not learning_plan:
            raise HTTPException(status_code=400, detail="Selected learning plan not found or inactive")

    # Enforce learning plan max_days constraint
    plan_max_days = learning_plan.get("max_days") if learning_plan else None
    final_assigned_days = assignment.assigned_days
    if plan_max_days and plan_max_days > 0:
        if final_assigned_days and final_assigned_days > plan_max_days:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot assign more than {plan_max_days} days. The learning plan '{learning_plan['name']}' allows a maximum of {plan_max_days} days."
            )
        if not final_assigned_days:
            final_assigned_days = plan_max_days

    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    credit_price = learning_plan['price'] if learning_plan else (pricing.get("class_price_student", 0) if pricing else 0)

    assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
    assigned_at = datetime.now(timezone.utc)
    expires_at = assigned_at + timedelta(hours=24)

    assignment_doc = {
        "assignment_id": assignment_id, "student_id": assignment.student_id,
        "student_name": student['name'], "student_email": student['email'],
        "teacher_id": assignment.teacher_id, "teacher_name": teacher['name'],
        "teacher_email": teacher['email'], "status": "pending",
        "payment_status": "unpaid",
        "credit_price": credit_price, "assigned_at": assigned_at.isoformat(),
        "approved_at": None, "expires_at": expires_at.isoformat(),
        "assigned_by": user.user_id,
        "learning_plan_id": assignment.learning_plan_id,
        "learning_plan_name": learning_plan['name'] if learning_plan else None,
        "learning_plan_price": learning_plan['price'] if learning_plan else None,
        "class_frequency": assignment.class_frequency if hasattr(assignment, 'class_frequency') else None,
        "specific_days": assignment.specific_days if hasattr(assignment, 'specific_days') else None,
        "demo_performance_notes": assignment.demo_performance_notes if hasattr(assignment, 'demo_performance_notes') else None,
        "assigned_days": final_assigned_days
    }
    await db.student_teacher_assignments.insert_one(assignment_doc)

    # Email notifications: student gets "your teacher is X", teacher gets "new class request"
    plan_label = learning_plan['name'] if learning_plan else 'standard plan'
    days_label = f"{final_assigned_days} sessions" if final_assigned_days else 'sessions'
    await notify_event(
        student.get('email'),
        f"You've been assigned to {teacher['name']}",
        f"Welcome to your learning journey, {student.get('name','')}!",
        f"Our counselor has assigned <b>{teacher['name']}</b> as your teacher for the <b>{plan_label}</b> ({days_label}). You'll receive class invitations soon.",
        cta_label="Open Dashboard",
        cta_url="https://edu.kaimeralearning.com/student-dashboard",
        event_key="student_assigned_for_student",
        vars={"student_name": student.get('name', ''), "teacher_name": teacher['name'], "plan_label": plan_label, "days_label": days_label},
    )
    await notify_event(
        teacher.get('email'),
        f"New Class Request — Student {student['name']}",
        "You have a new class request",
        f"<b>{student['name']}</b> has been assigned to you for the <b>{plan_label}</b> ({days_label}). Please review and accept within 24 hours from your teacher dashboard.",
        cta_label="Review Request",
        cta_url="https://edu.kaimeralearning.com/teacher-dashboard",
        event_key="student_assigned_for_teacher",
        vars={"student_name": student['name'], "teacher_name": teacher['name'], "plan_label": plan_label, "days_label": days_label},
    )
    return {"message": "Student assigned to teacher. Teacher has 24 hours to approve.", "assignment_id": assignment_id}


@router.get("/admin/emergency-assignments")
async def get_emergency_assignments(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    now = datetime.now(timezone.utc)
    pending_assignments = await db.student_teacher_assignments.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    emergency_assignments = []
    for a in pending_assignments:
        expires_at = datetime.fromisoformat(a['expires_at'])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            await db.student_teacher_assignments.update_one({"assignment_id": a['assignment_id']}, {"$set": {"status": "expired"}})
            a['status'] = "expired"
            emergency_assignments.append(a)
    return emergency_assignments


@router.get("/admin/all-assignments")
async def get_all_assignments(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    assignments = await db.student_teacher_assignments.find({}, {"_id": 0}).to_list(1000)
    for a in assignments:
        for field in ['assigned_at', 'expires_at']:
            if a.get(field) and isinstance(a[field], str):
                a[field] = datetime.fromisoformat(a[field])
        if a.get('approved_at') and isinstance(a['approved_at'], str):
            a['approved_at'] = datetime.fromisoformat(a['approved_at'])
    return assignments


@router.get("/admin/students")
async def get_all_students(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for student in students:
        if isinstance(student.get('created_at'), str):
            student['created_at'] = datetime.fromisoformat(student['created_at'])
    return students


@router.post("/admin/create-teacher")
async def create_teacher_account(teacher_data: CreateTeacherAccount, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counselor access only")
    validate_gmail(teacher_data.email)
    existing = await db.users.find_one({"email": teacher_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    # Auto-generate secure password — admin never sees it; sent only to user's email
    auto_password = generate_temp_password()
    password_hash_val = hash_password(auto_password)
    teacher_code = await generate_teacher_code()

    teacher_doc = {
        "user_id": user_id, "email": teacher_data.email, "name": teacher_data.name,
        "role": "teacher", "credits": 0.0, "picture": None,
        "password_hash": password_hash_val, "is_approved": True, "is_verified": False,
        "phone": None, "bio": None, "teacher_code": teacher_code,
        "bank_details": None, "badges": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(teacher_doc)

    # Send credentials directly to teacher (admin never sees password)
    creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
        <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{teacher_data.email}</p>
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
        <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{auto_password}</p>
        <p style="margin:8px 0 0;color:#dc2626;font-size:12px;">Please change this password after your first login.</p>
    </div>"""
    await notify_event(
        teacher_data.email,
        "Welcome to Kaimera Learning — Teacher Account Credentials",
        "Your Teacher Account is Ready",
        f"Hi {teacher_data.name}, your teacher account on Kaimera Learning has been created by the admin.",
        body_html=creds_html,
        cta_label="Sign In Now",
        cta_url="https://edu.kaimeralearning.com/login",
        event_key="teacher_account_created",
        vars={"name": teacher_data.name, "email": teacher_data.email, "temp_password": auto_password, "credentials_block": creds_html},
    )

    return {"message": "Teacher account created. Credentials emailed directly to the teacher.", "user_id": user_id, "email": teacher_data.email, "teacher_code": teacher_code}


@router.post("/admin/create-counsellor")
async def create_counsellor_account(counsellor_data: CreateTeacherAccount, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    validate_gmail(counsellor_data.email)
    existing = await db.users.find_one({"email": counsellor_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    counselor_id = f"KLC-{uuid.uuid4().hex[:6].upper()}"
    auto_password = generate_temp_password()
    password_hash_val = hash_password(auto_password)
    counsellor_doc = {
        "user_id": user_id, "email": counsellor_data.email, "name": counsellor_data.name,
        "role": "counsellor", "credits": 0.0, "picture": None,
        "password_hash": password_hash_val, "is_approved": True, "is_verified": False,
        "phone": None, "bio": None, "counselor_id": counselor_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(counsellor_doc)

    creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
        <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{counsellor_data.email}</p>
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
        <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{auto_password}</p>
        <p style="margin:8px 0 0;color:#dc2626;font-size:12px;">Please change this password after your first login.</p>
    </div>"""
    await notify_event(
        counsellor_data.email,
        "Welcome to Kaimera Learning — Counselor Account Credentials",
        "Your Counselor Account is Ready",
        f"Hi {counsellor_data.name}, your counselor account has been created by the admin.",
        body_html=creds_html,
        cta_label="Sign In Now",
        cta_url="https://edu.kaimeralearning.com/login",
        event_key="counsellor_account_created",
        vars={"name": counsellor_data.name, "email": counsellor_data.email, "temp_password": auto_password, "credentials_block": creds_html},
    )

    return {"message": "Counselor account created. Credentials emailed directly to the counselor.", "user_id": user_id, "email": counsellor_data.email, "counselor_id": counselor_id}


@router.post("/admin/create-user")
async def admin_create_user(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counselor access only")

    body = await request.json()
    role = body.get("role", "student")
    name = body.get("name", "").strip()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email and password are required")
    if role not in ["student", "teacher", "counsellor"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    validate_gmail(email)

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    phone = body.get("phone")
    if phone and str(phone).strip():
        phone_exists = await db.users.find_one({"phone": str(phone).strip()}, {"_id": 0, "email": 1})
        if phone_exists:
            raise HTTPException(status_code=400, detail=f"Phone number already registered with {phone_exists['email']}")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    # Auto-generate password — admin's input is ignored; never returned in JSON
    auto_password = generate_temp_password()
    password_hash_val = hash_password(auto_password)
    user_code = None

    base_doc = {
        "user_id": user_id, "email": email, "name": name, "role": role,
        "credits": 0.0, "picture": None, "password_hash": password_hash_val,
        "is_approved": True, "is_verified": False,
        "phone": phone, "bio": None, "badges": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    if role == "student":
        user_code = await generate_student_code()
        base_doc.update({"student_code": user_code, "institute": body.get("institute"), "goal": body.get("goal"), "preferred_time_slot": body.get("preferred_time_slot"), "state": body.get("state"), "city": body.get("city"), "country": body.get("country"), "grade": body.get("grade")})
    elif role == "teacher":
        user_code = await generate_teacher_code()
        base_doc.update({"teacher_code": user_code, "bank_details": None})

    await db.users.insert_one(base_doc)

    creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
        <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{email}</p>
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
        <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{auto_password}</p>
        <p style="margin:8px 0 0;color:#dc2626;font-size:12px;">Please change this password after your first login.</p>
    </div>"""
    await notify_event(
        email,
        f"Welcome to Kaimera Learning — {role.capitalize()} Account Credentials",
        f"Your {role.capitalize()} Account is Ready",
        f"Hi {name}, your {role} account on Kaimera Learning has been created.",
        body_html=creds_html,
        cta_label="Sign In Now",
        cta_url="https://edu.kaimeralearning.com/login",
        event_key="user_account_created",
        vars={"name": name, "email": email, "role": role, "role_capitalized": role.capitalize(), "temp_password": auto_password, "credentials_block": creds_html},
    )

    return {"message": f"{role.capitalize()} account created. Credentials emailed directly to the user.", "user_id": user_id, "email": email, "user_code": user_code}


@router.post("/admin/set-pricing")
async def set_system_pricing(pricing: SystemPricing, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    pricing_doc = {"pricing_id": "system_pricing", "demo_price_student": pricing.demo_price_student, "class_price_student": pricing.class_price_student, "demo_earning_teacher": pricing.demo_earning_teacher, "class_earning_teacher": pricing.class_earning_teacher, "cancel_rating_deduction": pricing.cancel_rating_deduction, "completion_rating_boost": pricing.completion_rating_boost, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.user_id}
    await db.system_pricing.update_one({"pricing_id": "system_pricing"}, {"$set": pricing_doc}, upsert=True)
    return {"message": "System pricing updated successfully"}


@router.get("/admin/get-pricing")
async def get_system_pricing(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Access denied")
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    if not pricing:
        return {"demo_price_student": 0.0, "class_price_student": 0.0, "demo_earning_teacher": 0.0, "class_earning_teacher": 0.0, "cancel_rating_deduction": 0.2, "completion_rating_boost": 0.1}
    if isinstance(pricing.get('updated_at'), str):
        pricing['updated_at'] = datetime.fromisoformat(pricing['updated_at'])
    return pricing


# ─── Learning Plans CRUD ───

@router.post("/admin/learning-plans")
async def create_learning_plan(plan: LearningPlan, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    plan_doc = {
        "plan_id": plan_id, "name": plan.name, "price": plan.price,
        "details": plan.details, "max_days": plan.max_days, "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.user_id
    }
    await db.learning_plans.insert_one(plan_doc)
    return {"message": "Learning plan created", "plan_id": plan_id}


@router.get("/admin/learning-plans")
async def list_learning_plans(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Access denied")
    plans = await db.learning_plans.find({"is_active": True}, {"_id": 0}).to_list(100)
    return plans


@router.put("/admin/learning-plans/{plan_id}")
async def update_learning_plan(plan_id: str, plan: LearningPlan, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    existing = await db.learning_plans.find_one({"plan_id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    await db.learning_plans.update_one(
        {"plan_id": plan_id},
        {"$set": {"name": plan.name, "price": plan.price, "details": plan.details, "max_days": plan.max_days}}
    )
    return {"message": "Learning plan updated"}


@router.delete("/admin/learning-plans/{plan_id}")
async def delete_learning_plan(plan_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    await db.learning_plans.update_one({"plan_id": plan_id}, {"$set": {"is_active": False}})
    return {"message": "Learning plan deactivated"}


@router.get("/admin/teacher-ratings")
async def admin_teacher_ratings(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    teachers = await db.users.find(
        {"role": "teacher"},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "teacher_code": 1, "star_rating": 1, "rating_details": 1, "is_suspended": 1, "suspended_until": 1, "monthly_cancellations": 1}
    ).to_list(500)
    return teachers


@router.get("/admin/teacher-classes/{teacher_id}")
async def admin_teacher_classes(teacher_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin/Counsellor views all classes for a teacher with full session timeline"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    teacher = await db.users.find_one({"user_id": teacher_id, "role": "teacher"}, {"_id": 0, "password_hash": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Get all classes for this teacher
    classes = await db.class_sessions.find(
        {"teacher_id": teacher_id}, {"_id": 0}
    ).sort("date", -1).to_list(500)

    # Enrich each class with attendance and proof data
    for cls in classes:
        class_id = cls["class_id"]
        student_id = cls.get("assigned_student_id", "")

        # Get attendance for this class
        attendance = await db.attendance.find(
            {"class_id": class_id}, {"_id": 0, "date": 1, "status": 1, "student_name": 1, "reason": 1, "off_day_marking": 1}
        ).sort("date", 1).to_list(100)
        cls["attendance_records"] = attendance

        # Get proofs for this class
        proofs = await db.class_proofs.find(
            {"class_id": class_id}, {"_id": 0, "proof_id": 1, "proof_date": 1, "status": 1, "admin_status": 1, "meeting_duration_minutes": 1, "submitted_at": 1}
        ).sort("proof_date", 1).to_list(50)
        cls["proof_records"] = proofs

        # Summary stats
        session_history = cls.get("session_history", [])
        cls["total_sessions_conducted"] = sum(1 for s in session_history if s.get("status") == "conducted")
        cls["total_sessions_cancelled"] = sum(1 for s in session_history if "cancel" in s.get("status", ""))
        cls["total_sessions_auto_cancelled"] = sum(1 for s in session_history if s.get("status") == "auto_cancelled")

    # Summary for this teacher
    summary = {
        "total_classes": len(classes),
        "completed": sum(1 for c in classes if c.get("status") == "completed"),
        "scheduled": sum(1 for c in classes if c.get("status") == "scheduled"),
        "in_progress": sum(1 for c in classes if c.get("status") == "in_progress"),
        "transferred": sum(1 for c in classes if c.get("status") == "transferred")
    }

    return {"teacher": teacher, "classes": classes, "summary": summary}


@router.get("/admin/class-detail/{class_id}")
async def admin_class_detail(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin/Counsellor views detailed timeline for a single class"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Full attendance
    attendance = await db.attendance.find(
        {"class_id": class_id}, {"_id": 0}
    ).sort("date", 1).to_list(200)

    # Full proofs
    proofs = await db.class_proofs.find(
        {"class_id": class_id}, {"_id": 0, "screenshot_base64": 0}
    ).sort("proof_date", 1).to_list(50)

    # Assignment info
    assignment = None
    if cls.get("assigned_student_id"):
        assignment = await db.student_teacher_assignments.find_one(
            {"teacher_id": cls["teacher_id"], "student_id": cls["assigned_student_id"]},
            {"_id": 0}
        )

    return {
        "class": cls,
        "attendance": attendance,
        "proofs": proofs,
        "assignment": assignment,
        "session_history": cls.get("session_history", []),
        "sessions_conducted": cls.get("sessions_conducted", 0),
        "duration_days": cls.get("duration_days", 1)
    }



@router.post("/admin/create-student")
async def admin_create_student(student_data: CreateStudentAccount, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counselor access only")
    validate_gmail(student_data.email)
    existing = await db.users.find_one({"email": student_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if student_data.phone and student_data.phone.strip():
        phone_exists = await db.users.find_one({"phone": student_data.phone.strip()}, {"_id": 0, "email": 1})
        if phone_exists:
            raise HTTPException(status_code=400, detail=f"Phone number already registered with {phone_exists['email']}")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    auto_password = generate_temp_password()
    password_hash_val = hash_password(auto_password)
    student_code = await generate_student_code()

    student_doc = {
        "user_id": user_id, "email": student_data.email, "name": student_data.name,
        "role": "student", "credits": 0.0, "picture": None, "password_hash": password_hash_val,
        "is_approved": True, "is_verified": False,
        "phone": student_data.phone, "bio": None,
        "institute": student_data.institute, "goal": student_data.goal,
        "preferred_time_slot": student_data.preferred_time_slot,
        "state": student_data.state, "city": student_data.city, "country": student_data.country,
        "grade": student_data.grade, "student_code": student_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(student_doc)

    creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
        <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{student_data.email}</p>
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
        <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{auto_password}</p>
        <p style="margin:8px 0 0;color:#dc2626;font-size:12px;">Please change this password after your first login.</p>
    </div>"""
    await notify_event(
        student_data.email,
        "Welcome to Kaimera Learning — Student Account Credentials",
        "Your Student Account is Ready",
        f"Hi {student_data.name}, your student account on Kaimera Learning has been created.",
        body_html=creds_html,
        cta_label="Sign In Now",
        cta_url="https://edu.kaimeralearning.com/login",
        event_key="student_account_created",
        vars={"name": student_data.name, "email": student_data.email, "temp_password": auto_password, "credentials_block": creds_html},
    )

    return {"message": "Student account created. Credentials emailed directly to the student.", "user_id": user_id, "email": student_data.email, "name": student_data.name, "student_code": student_code}


@router.post("/admin/reset-password")
async def admin_reset_password(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    body = await request.json()
    target_email = body.get("email")
    target_user_id = body.get("user_id")
    new_password = body.get("new_password")
    if not target_email and not target_user_id:
        raise HTTPException(status_code=400, detail="email or user_id required")

    query = {"email": target_email} if target_email else {"user_id": target_user_id}
    target = await db.users.find_one(query, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # If admin didn't provide a password, auto-generate one (preferred — admin never sees it)
    if not new_password:
        new_password = generate_temp_password()
    password_hash_val = hash_password(new_password)
    await db.users.update_one({"user_id": target["user_id"]}, {"$set": {"password_hash": password_hash_val}})
    # Invalidate all existing sessions for this user
    await db.user_sessions.delete_many({"user_id": target["user_id"]})

    creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
        <p style="margin:0 0 8px;color:#475569;font-size:14px;">New Temporary Password:</p>
        <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{new_password}</p>
        <p style="margin:8px 0 0;color:#dc2626;font-size:12px;">All existing sessions have been signed out. Please change this password after sign-in.</p>
    </div>"""
    await notify_event(
        target["email"],
        "Kaimera Learning — Password Reset by Admin",
        "Your Password Was Reset",
        f"Hi {target.get('name','')}, an administrator has reset your account password.",
        body_html=creds_html,
        cta_label="Sign In Now",
        cta_url="https://edu.kaimeralearning.com/login",
        event_key="password_reset_by_admin",
        vars={"name": target.get('name', ''), "email": target["email"], "new_password": new_password, "credentials_block": creds_html},
    )
    return {"message": f"Password reset for {target['name']} ({target['email']}). New password emailed directly. All sessions invalidated.", "role": target["role"], "email": target["email"], "user_id": target["user_id"]}


@router.get("/admin/search-users-for-reset")
async def admin_search_users_for_reset(q: str = "", role: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    query = {}
    if role and role != "all":
        query["role"] = role
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}, {"user_id": {"$regex": q, "$options": "i"}}, {"teacher_code": {"$regex": q, "$options": "i"}}, {"student_code": {"$regex": q, "$options": "i"}}]
    users = await db.users.find(query, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "teacher_code": 1, "student_code": 1}).to_list(50)
    return users


@router.get("/admin/all-users")
async def admin_get_all_users(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    users_list = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(5000)
    return users_list


@router.get("/admin/user-detail/{user_id}")
async def admin_get_user_detail(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
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
    # Enrich drawer transactions with reference
    txns = result["transactions"]
    cls_ids = list({t.get("class_id") for t in txns if t.get("class_id")})
    pay_ids = list({t.get("payment_id") for t in txns if t.get("payment_id")})
    cp_ids = list({t.get("counterparty_user_id") for t in txns if t.get("counterparty_user_id")})
    cls_m, pay_m, cp_m = {}, {}, {}
    if cls_ids:
        for c in await db.class_sessions.find({"class_id": {"$in": cls_ids}}, {"_id": 0, "class_id": 1, "title": 1, "date": 1, "teacher_name": 1}).to_list(len(cls_ids)):
            cls_m[c["class_id"]] = c
    if pay_ids:
        for p in await db.payments.find({"payment_id": {"$in": pay_ids}}, {"_id": 0, "payment_id": 1, "receipt_id": 1, "razorpay_payment_id": 1}).to_list(len(pay_ids)):
            pay_m[p["payment_id"]] = p
    if cp_ids:
        for u in await db.users.find({"user_id": {"$in": cp_ids}}, {"_id": 0, "user_id": 1, "name": 1, "role": 1}).to_list(len(cp_ids)):
            cp_m[u["user_id"]] = u
    for t in txns:
        ref = {}
        if t.get("class_id") and cls_m.get(t["class_id"]):
            c = cls_m[t["class_id"]]; ref.update({"class_title": c.get("title"), "class_date": c.get("date"), "teacher_name": c.get("teacher_name")})
        if t.get("payment_id") and pay_m.get(t["payment_id"]):
            p = pay_m[t["payment_id"]]; ref.update({"payment_id": p["payment_id"], "receipt_id": p.get("receipt_id"), "razorpay_payment_id": p.get("razorpay_payment_id")})
        if t.get("counterparty_user_id") and cp_m.get(t["counterparty_user_id"]):
            cp = cp_m[t["counterparty_user_id"]]; ref.update({"counterparty_name": cp.get("name"), "counterparty_role": cp.get("role")})
        t["reference"] = ref
    return result


@router.post("/admin/assign-badge")
async def assign_badge(data: BadgeAssign, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    target = await db.users.find_one({"user_id": data.user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] not in ["teacher", "counsellor"]:
        raise HTTPException(status_code=400, detail="Badges can only be assigned to teachers or counselors")
    await db.users.update_one({"user_id": data.user_id}, {"$addToSet": {"badges": data.badge_name}})
    await db.notifications.insert_one({"notification_id": f"notif_{uuid.uuid4().hex[:12]}", "user_id": data.user_id, "type": "badge_assigned", "title": "New Badge Earned!", "message": f"You've been awarded the '{data.badge_name}' badge by admin.", "read": False, "related_id": data.badge_name, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"message": f"Badge '{data.badge_name}' assigned to {target['name']}"}


@router.delete("/admin/remove-badge")
async def remove_badge(user_id: str, badge_name: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    await db.users.update_one({"user_id": user_id}, {"$pull": {"badges": badge_name}})
    return {"message": f"Badge '{badge_name}' removed"}


@router.post("/admin/badge-template")
async def create_badge_template(request: Request, authorization: Optional[str] = Header(None)):
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
    await db.badge_templates.insert_one({"badge_id": f"badge_{uuid.uuid4().hex[:8]}", "name": name, "description": body.get("description", ""), "color": body.get("color", "#8b5cf6"), "created_at": datetime.now(timezone.utc).isoformat()})
    return {"message": f"Badge '{name}' created"}


@router.get("/admin/badge-templates")
async def get_badge_templates(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    templates = await db.badge_templates.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return templates


@router.delete("/admin/badge-template/{badge_id}")
async def delete_badge_template(badge_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    await db.badge_templates.delete_one({"badge_id": badge_id})
    return {"message": "Badge template deleted"}


@router.get("/admin/approved-proofs")
async def get_admin_pending_proofs(date_from: Optional[str] = None, date_to: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
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
    for proof in proofs:
        cls = await db.class_sessions.find_one({"class_id": proof.get("class_id")}, {"_id": 0})
        if cls:
            proof["class_details"] = {"title": cls.get("title"), "subject": cls.get("subject"), "date": cls.get("date"), "end_date": cls.get("end_date"), "is_demo": cls.get("is_demo", False), "start_time": cls.get("start_time"), "end_time": cls.get("end_time"), "enrolled_students": cls.get("enrolled_students", [])}
        student = await db.users.find_one({"user_id": proof.get("student_id")}, {"_id": 0, "password_hash": 0})
        if student:
            proof["student_details"] = {"name": student.get("name"), "email": student.get("email"), "grade": student.get("grade")}
        teacher = await db.users.find_one({"user_id": proof.get("teacher_id")}, {"_id": 0, "password_hash": 0})
        if teacher:
            proof["teacher_details"] = {"name": teacher.get("name"), "email": teacher.get("email"), "teacher_code": teacher.get("teacher_code")}
    return proofs


@router.post("/admin/approve-proof")
async def admin_approve_proof(data: AdminProofApproval, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    proof = await db.class_proofs.find_one({"proof_id": data.proof_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof.get("admin_status") != "pending":
        raise HTTPException(status_code=400, detail="Proof not pending admin approval")

    new_status = "approved" if data.approved else "rejected"
    update_set = {
        "admin_status": new_status,
        "admin_reviewed_by": user.user_id,
        "admin_reviewed_at": datetime.now(timezone.utc).isoformat(),
        "admin_notes": data.admin_notes
    }
    if not data.approved:
        # Increment rejection counter; lock credit if this is the 2nd+ rejection
        new_rej = (proof.get("rejection_count") or 0) + 1
        update_set["rejection_count"] = new_rej
        if new_rej >= 2:
            update_set["credit_blocked"] = True
        # Notify teacher to resubmit (or final-block if 2nd rejection)
        msg_extra = " (FINAL: this session will not be credited even if next submission is approved.)" if new_rej >= 2 else " Please resubmit a new proof."
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": proof['teacher_id'], "type": "proof_rejected",
            "title": "Proof Rejected by Admin — Resubmit",
            "message": f"Admin rejected your proof for '{proof.get('class_title', '')}'. Reason: {data.admin_notes or 'No reason given'}.{msg_extra}",
            "read": False, "related_id": data.proof_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    await db.class_proofs.update_one({"proof_id": data.proof_id}, {"$set": update_set})

    if data.approved and not proof.get("credit_blocked"):
        pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
        if pricing:
            cls = await db.class_sessions.find_one({"class_id": proof['class_id']}, {"_id": 0})
            earning = pricing.get('demo_earning_teacher', 0) if cls and cls.get('is_demo') else pricing.get('class_earning_teacher', 0)
            if earning > 0:
                await db.users.update_one({"user_id": proof['teacher_id']}, {"$inc": {"credits": earning}})
                await db.transactions.insert_one({"transaction_id": f"txn_{uuid.uuid4().hex[:12]}", "user_id": proof['teacher_id'], "type": "earning", "amount": earning, "description": f"Admin approved: {proof.get('class_title', 'Class')}", "proof_id": data.proof_id, "class_id": proof['class_id'], "counterparty_user_id": user.user_id, "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()})
                # Mirror: platform paid out earning to teacher
                await insert_admin_mirror_txn(
                    amount=-earning,
                    description=f"Earning paid to teacher {proof.get('teacher_name','')} for '{proof.get('class_title','Class')}'",
                    txn_type="earning_paid",
                    proof_id=data.proof_id,
                    class_id=proof['class_id'],
                    counterparty_user_id=proof['teacher_id']
                )
                await db.notifications.insert_one({"notification_id": f"notif_{uuid.uuid4().hex[:12]}", "user_id": proof['teacher_id'], "type": "credit_earned", "title": "Credits Earned!", "message": f"{earning} credits added to your wallet for '{proof.get('class_title', 'Class')}'.", "read": False, "related_id": data.proof_id, "created_at": datetime.now(timezone.utc).isoformat()})

            # Check if all classes for this teacher-student assignment are completed with approved proofs
            if cls:
                student_id = cls.get("assigned_student_id")
                teacher_id = proof['teacher_id']
                if student_id:
                    # Find the assignment
                    assignment = await db.student_teacher_assignments.find_one(
                        {"teacher_id": teacher_id, "student_id": student_id, "status": "approved", "payment_status": "paid"},
                        {"_id": 0}
                    )
                    if assignment:
                        # Get all classes for this assignment
                        all_classes = await db.class_sessions.find(
                            {"teacher_id": teacher_id, "assigned_student_id": student_id,
                             "status": {"$in": ["scheduled", "in_progress", "completed"]}},
                            {"_id": 0, "class_id": 1, "status": 1}
                        ).to_list(100)

                        # Check if ALL are completed
                        all_completed = len(all_classes) > 0 and all(c.get("status") == "completed" for c in all_classes)

                        if all_completed:
                            # Check all have approved proofs
                            class_ids = [c["class_id"] for c in all_classes]
                            approved_proofs = await db.class_proofs.count_documents(
                                {"class_id": {"$in": class_ids}, "admin_status": "approved"}
                            )
                            # At least one proof per class approved
                            if approved_proofs >= len(all_classes):
                                # All classes completed with proofs approved — boost rating!
                                boost = pricing.get("completion_rating_boost", 0.1)
                                from services.rating import record_rating_event
                                await record_rating_event(
                                    teacher_id, "completion_boost",
                                    f"Successfully completed all {len(all_classes)} classes for student {assignment.get('student_name')}"
                                )

    action = "approved & teacher credited" if data.approved else "rejected"
    return {"message": f"Proof {action} by admin"}


@router.get("/admin/complaints")
async def get_all_complaints(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    complaints = await db.complaints.find({}, {"_id": 0}).to_list(1000)
    return complaints


@router.post("/admin/resolve-complaint")
async def resolve_complaint(resolution: ComplaintResolve, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    complaint = await db.complaints.find_one({"complaint_id": resolution.complaint_id}, {"_id": 0})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    await db.complaints.update_one({"complaint_id": resolution.complaint_id}, {"$set": {"status": resolution.status, "resolution": resolution.resolution, "resolved_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": f"Complaint {resolution.status}"}


@router.post("/admin/grant-demo-extra")
async def grant_demo_extra(data: DemoExtraGrant, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    existing = await db.demo_extras.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Extra demo already granted for this email")
    await db.demo_extras.insert_one({"email": data.email, "extra_count": 1, "granted_by": user.user_id, "granted_at": datetime.now(timezone.utc).isoformat()})
    await db.history_logs.insert_one({"log_id": f"log_{uuid.uuid4().hex[:12]}", "action": "demo_extra_granted", "actor_id": user.user_id, "actor_name": user.name, "actor_role": "admin", "target_type": "student", "target_id": data.email, "details": f"Admin granted 1 extra demo to {data.email}", "created_at": datetime.now(timezone.utc).isoformat()})
    return {"message": f"Extra demo granted to {data.email}"}


@router.post("/admin/learning-kit/upload")
async def upload_learning_kit(title: str = Form(...), grade: str = Form(...), description: str = Form(""), file: UploadFile = File(...), request: Request = None, authorization: Optional[str] = Header(None)):
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

    kit_doc = {"kit_id": kit_id, "title": title, "grade": grade, "description": description, "file_name": file.filename, "stored_name": safe_filename, "file_type": ext, "file_size": len(content), "uploaded_by": user.user_id, "uploaded_by_name": user.name, "created_at": datetime.now(timezone.utc).isoformat()}
    insert_doc = kit_doc.copy()
    await db.learning_kits.insert_one(insert_doc)
    return {"message": f"Learning kit '{title}' uploaded for Grade {grade}", "kit_id": kit_id}


@router.delete("/admin/learning-kit/{kit_id}")
async def delete_learning_kit(kit_id: str, request: Request, authorization: Optional[str] = Header(None)):
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


@router.get("/admin/counsellor-tracking")
async def admin_counsellor_tracking(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    counsellors = await db.users.find({"role": "counsellor"}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(100)
    result = []
    for c in counsellors:
        cid = c["user_id"]
        assignments = await db.student_teacher_assignments.find({"assigned_by": cid}, {"_id": 0}).to_list(1000)
        active_count = sum(1 for a in assignments if a.get("status") == "approved")
        pending_count = sum(1 for a in assignments if a.get("status") == "pending")
        rejected_count = sum(1 for a in assignments if a.get("status") == "rejected")
        result.append({"user_id": cid, "name": c.get("name", ""), "email": c.get("email", ""), "phone": c.get("phone", ""), "badges": c.get("badges", []), "total_assignments": len(assignments), "active_assignments": active_count, "pending_assignments": pending_count, "rejected_assignments": rejected_count, "created_at": c.get("created_at", "")})
    return result


@router.get("/admin/counsellor-daily-stats/{counsellor_id}")
async def admin_counsellor_daily_stats(counsellor_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    assignments = await db.student_teacher_assignments.find({"assigned_by": counsellor_id}, {"_id": 0}).to_list(1000)
    logs = await db.history_logs.find({"actor_id": counsellor_id}, {"_id": 0}).to_list(2000)
    daily = defaultdict(lambda: {"leads": 0, "allotments": 0, "sessions": 0})
    for a in assignments:
        date_str = a.get("assigned_at", "")[:10]
        if date_str:
            daily[date_str]["allotments"] += 1
    for log in logs:
        date_str = log.get("created_at", "")[:10]
        if date_str:
            action = log.get("action", "")
            if "demo" in action:
                daily[date_str]["leads"] += 1
            if "session" in action or "class" in action or "proof" in action:
                daily[date_str]["sessions"] += 1
    sorted_days = sorted(daily.items(), key=lambda x: x[0])[-30:]
    result = [{"date": d, **stats} for d, stats in sorted_days]
    return result


@router.post("/admin/edit-student/{user_id}")
async def admin_edit_student(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    body = await request.json()
    target = await db.users.find_one({"user_id": user_id, "role": "student"}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Student not found")

    # Email uniqueness check if changing email
    if "email" in body and body["email"] and body["email"] != target.get("email"):
        email_exists = await db.users.find_one({"email": body["email"], "user_id": {"$ne": user_id}}, {"_id": 0})
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already registered with another account")

    # Phone uniqueness check if changing phone
    if "phone" in body and body["phone"] and str(body["phone"]).strip():
        phone_exists = await db.users.find_one({"phone": str(body["phone"]).strip(), "user_id": {"$ne": user_id}}, {"_id": 0})
        if phone_exists:
            raise HTTPException(status_code=400, detail="Phone number already registered with another account")

    editable_fields = ["name", "email", "phone", "institute", "goal", "preferred_time_slot", "state", "city", "country", "grade", "credits", "bio"]
    updates = {}
    for field in editable_fields:
        if field in body and body[field] is not None:
            if field == "credits":
                updates[field] = float(body[field])
            else:
                updates[field] = body[field]
    if updates:
        await db.users.update_one({"user_id": user_id}, {"$set": updates})
    return {"message": "Student profile updated", "updated_fields": list(updates.keys())}


@router.post("/admin/block-user")
async def admin_block_user(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    body = await request.json()
    target_id = body.get("user_id")
    blocked = body.get("blocked", True)
    target = await db.users.find_one({"user_id": target_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "admin":
        raise HTTPException(status_code=400, detail="Cannot block admin accounts")
    await db.users.update_one({"user_id": target_id}, {"$set": {"is_blocked": blocked}})
    if blocked:
        await db.user_sessions.delete_many({"user_id": target_id})
    action = "blocked" if blocked else "unblocked"
    return {"message": f"User {target['name']} {action} successfully"}


@router.post("/admin/delete-user")
async def admin_delete_user(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    body = await request.json()
    target_id = body.get("user_id")
    target = await db.users.find_one({"user_id": target_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin accounts")
    await db.users.delete_one({"user_id": target_id})
    await db.user_sessions.delete_many({"user_id": target_id})
    return {"message": f"User {target['name']} ({target['email']}) deleted permanently"}


@router.post("/admin/purge-system")
async def admin_purge_system(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    collections_to_clear = [
        "class_sessions", "student_teacher_assignments", "transactions",
        "payment_transactions", "complaints", "class_proofs", "feedback",
        "notifications", "demo_requests", "demo_extras", "demo_feedback",
        "history_logs", "teacher_student_feedback", "renewal_meetings",
        "learning_kits", "teacher_calendar", "badge_templates", "system_pricing"
    ]
    for coll_name in collections_to_clear:
        await db[coll_name].delete_many({})

    await db.users.delete_many({"role": {"$ne": "admin"}})
    await db.user_sessions.delete_many({"user_id": {"$nin": [u["user_id"] async for u in db.users.find({"role": "admin"}, {"_id": 0, "user_id": 1})]}})
    await db.counters.delete_many({})

    return {"message": "System purged. Only admin accounts remain. All counters reset to zero."}



@router.post("/admin/update-bank-details/{user_id}")
async def admin_update_bank_details(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin-only: update bank details for teacher or counselor"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    body = await request.json()
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") not in ["teacher", "counsellor"]:
        raise HTTPException(status_code=400, detail="Bank details can only be set for teachers or counselors")

    updates = {}
    for field in ["bank_name", "bank_account_number", "bank_ifsc_code"]:
        if field in body and body[field]:
            updates[field] = body[field]

    if updates:
        await db.users.update_one({"user_id": user_id}, {"$set": updates})
    return {"message": "Bank details updated", "updated_fields": list(updates.keys())}


# ─── Email Config (live editable from Admin UI, no restart needed) ───────────
@router.get("/admin/email-config")
async def get_email_config(request: Request, authorization: Optional[str] = Header(None)):
    """Returns the active email config. Password is masked."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    cfg = await _get_email_config()
    pwd = cfg.get("password") or ""
    db_doc = await db.system_config.find_one({"config_id": "email"}, {"_id": 0})
    return {
        "active_sender_email": cfg.get("email"),
        "password_set": bool(pwd),
        "password_length": len(pwd),
        "password_masked": (pwd[:2] + "•" * max(0, len(pwd) - 4) + pwd[-2:]) if len(pwd) > 4 else "",
        "source": "database" if db_doc else "env",
        "db_override": {
            "sender_email": (db_doc or {}).get("sender_email"),
            "has_app_password": bool((db_doc or {}).get("app_password")),
            "updated_at": (db_doc or {}).get("updated_at"),
            "updated_by": (db_doc or {}).get("updated_by"),
        }
    }


@router.post("/admin/email-config")
async def update_email_config(request: Request, authorization: Optional[str] = Header(None)):
    """Update sender email and/or app password. Takes effect within 30s (cache TTL).
    Pass clear_db=true to remove the DB override and fall back to .env values.
    """
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    if body.get("clear_db"):
        await db.system_config.delete_one({"config_id": "email"})
        invalidate_email_config_cache()
        return {"message": "Database override cleared. Falling back to .env values."}

    sender_email = (body.get("sender_email") or "").strip()
    app_password = (body.get("app_password") or "").replace(" ", "")  # strip whitespace from pasted app passwords
    if not sender_email and not app_password:
        raise HTTPException(status_code=400, detail="Provide sender_email and/or app_password")
    if app_password and len(app_password) < 12:
        raise HTTPException(status_code=400, detail="App password should be at least 12 chars (Gmail App Passwords are 16)")

    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.user_id}
    if sender_email:
        update["sender_email"] = sender_email
    if app_password:
        update["app_password"] = app_password
    await db.system_config.update_one({"config_id": "email"}, {"$set": {"config_id": "email", **update}}, upsert=True)
    invalidate_email_config_cache()
    return {"message": "Email config saved. Test it now to verify.", "saved_fields": [k for k in update if k not in ("updated_at", "updated_by")]}


@router.post("/admin/email-test")
async def test_email_config(request: Request, authorization: Optional[str] = Header(None)):
    """Send a test email using the current active config. Returns the actual SMTP error (if any) so admin can debug."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    to = (body.get("to") or user.email or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="Provide a 'to' email address")

    invalidate_email_config_cache()  # always re-read latest config for the test
    html = f"""<div style='font-family:Arial;padding:24px;background:#f8fafc;border-radius:12px;'>
        <h2 style='color:#0ea5e9;margin:0 0 8px;'>Kaimera Email Test</h2>
        <p>If you can read this, your Gmail SMTP config is working correctly. ✅</p>
        <p style='color:#64748b;font-size:12px;'>Triggered by: {user.email}<br/>At: {datetime.now(timezone.utc).isoformat()}</p>
    </div>"""
    result = await send_email(to, "Kaimera Email Test", html)
    if not result or (isinstance(result, dict) and result.get("error")):
        err = (result or {}).get("error", "unknown error")
        return {"ok": False, "error": err, "to": to}
    return {"ok": True, "message": f"Test email queued for {to}. Check the inbox in a few seconds.", "to": to}



# ─── Email Template Editor (admin) ────────────────────────────────────────────

EMAIL_MEDIA_DIR = UPLOADS_DIR / "email_media"
EMAIL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EMAIL_MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
                           ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


@router.get("/admin/email-events")
async def list_email_events(request: Request, authorization: Optional[str] = Header(None)):
    """Returns the registry of all email events with their default templates and which are overridden."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    from services.email_templates import EMAIL_EVENTS
    overrides = {d["event_key"]: d for d in await db.email_templates.find({}, {"_id": 0}).to_list(200)}
    out = []
    for key, ev in EMAIL_EVENTS.items():
        ovr = overrides.get(key, {})
        out.append({
            "event_key": key,
            "name": ev["name"],
            "description": ev["description"],
            "variables": ev["variables"],
            "is_overridden": bool(ovr),
            "default": {f: ev.get(f, "") for f in ("subject", "title", "intro", "body_html", "cta_label", "cta_url")},
            "override": {f: ovr.get(f, "") for f in ("subject", "title", "intro", "body_html", "cta_label", "cta_url")} if ovr else {},
            "inline_image_id": ovr.get("inline_image_id"),
            "logo_url": ovr.get("logo_url") or "",
            "attachment_ids": ovr.get("attachment_ids", []) or [],
        })
    return out


@router.put("/admin/email-templates/{event_key}")
async def save_email_template(event_key: str, request: Request, authorization: Optional[str] = Header(None)):
    """Save admin override for a specific email event. Empty fields fall back to defaults at send time."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    from services.email_templates import EMAIL_EVENTS, invalidate_template_cache
    if event_key not in EMAIL_EVENTS:
        raise HTTPException(status_code=404, detail="Unknown event_key")
    body = await request.json()
    update = {
        "event_key": event_key,
        "subject": (body.get("subject") or "").strip(),
        "title": (body.get("title") or "").strip(),
        "intro": body.get("intro") or "",
        "body_html": body.get("body_html") or "",
        "cta_label": (body.get("cta_label") or "").strip(),
        "cta_url": (body.get("cta_url") or "").strip(),
        "inline_image_id": body.get("inline_image_id") or None,
        "logo_url": (body.get("logo_url") or "").strip() or None,
        "attachment_ids": body.get("attachment_ids") or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user.user_id,
    }
    await db.email_templates.update_one({"event_key": event_key}, {"$set": update}, upsert=True)
    invalidate_template_cache()
    return {"message": "Template saved", "event_key": event_key}


@router.delete("/admin/email-templates/{event_key}")
async def reset_email_template(event_key: str, request: Request, authorization: Optional[str] = Header(None)):
    """Restore the default template (deletes admin override)."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    from services.email_templates import invalidate_template_cache
    await db.email_templates.delete_one({"event_key": event_key})
    invalidate_template_cache()
    return {"message": "Template reset to default"}


@router.post("/admin/email-templates/{event_key}/test")
async def test_email_template(event_key: str, request: Request, authorization: Optional[str] = Header(None)):
    """Send the resolved template (with sample data) to a test recipient. Returns real SMTP status."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    from services.email_templates import EMAIL_EVENTS, invalidate_template_cache, resolve_template
    from services.helpers import _wrap_email_html, _resolve_template_media, send_email
    if event_key not in EMAIL_EVENTS:
        raise HTTPException(status_code=404, detail="Unknown event_key")
    body = await request.json()
    to = (body.get("to") or user.email or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="Provide a 'to' email")
    sample_vars = body.get("vars") or {}
    # Provide defaults so {{var}} substitution doesn't leave gaps
    for v in EMAIL_EVENTS[event_key]["variables"]:
        sample_vars.setdefault(v, f"[{v}]")
    invalidate_template_cache()
    tpl = await resolve_template(event_key, sample_vars)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template missing")
    inline_images, attachments = await _resolve_template_media(tpl.get("inline_image_id"), tpl.get("attachment_ids", []))
    logo_cid = "logo" if inline_images else ""
    logo_url = tpl.get("logo_url") or ""
    html = _wrap_email_html(tpl["title"], tpl["intro"], tpl["body_html"], tpl["cta_label"], tpl["cta_url"],
                            inline_logo_cid=logo_cid, logo_url=logo_url)
    result = await send_email(to, tpl["subject"], html, inline_images=inline_images, attachments=attachments)
    if not result or (isinstance(result, dict) and result.get("error")):
        err = (result or {}).get("error", "unknown error")
        return {"ok": False, "error": err, "to": to}
    return {"ok": True, "message": f"Test email sent to {to}", "to": to}


# ─── Email Media Library (logos / attachments) ────────────────────────────────

@router.post("/admin/email-media")
async def upload_email_media(file: UploadFile = File(...), kind: str = Form("auto"),
                             request: Request = None, authorization: Optional[str] = Header(None)):
    """Upload an image or file to the shared email media library. Reusable across templates."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EMAIL_MEDIA_EXT:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed.")
    detected_kind = "image" if ext in IMAGE_EXT else "file"
    if kind not in ("auto", "image", "file"):
        raise HTTPException(status_code=400, detail="kind must be auto/image/file")
    final_kind = detected_kind if kind == "auto" else kind
    if final_kind == "image" and ext not in IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Selected kind=image but file is not an image")

    media_id = f"em_{uuid.uuid4().hex[:12]}"
    safe_name = f"{media_id}{ext}"
    dest = EMAIL_MEDIA_DIR / safe_name
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    with open(dest, "wb") as fh:
        fh.write(content)

    # Best-effort mime type
    import mimetypes
    mime, _ = mimetypes.guess_type(file.filename or "")
    doc = {
        "media_id": media_id,
        "filename": file.filename,
        "stored_name": safe_name,
        "mime": mime or "application/octet-stream",
        "size": len(content),
        "kind": final_kind,
        "uploaded_by": user.user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.email_media.insert_one(doc.copy())
    return {"message": "Uploaded", "media": doc}


@router.get("/admin/email-media")
async def list_email_media(request: Request, authorization: Optional[str] = Header(None),
                           kind: Optional[str] = None):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    q = {}
    if kind in ("image", "file"):
        q["kind"] = kind
    items = await db.email_media.find(q, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    return items


@router.get("/admin/email-media/file/{media_id}")
async def get_email_media_file(media_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Serve the raw file for preview in the admin UI."""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    m = await db.email_media.find_one({"media_id": media_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Media not found")
    p = EMAIL_MEDIA_DIR / m["stored_name"]
    if not p.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    from fastapi.responses import FileResponse
    return FileResponse(str(p), media_type=m.get("mime") or "application/octet-stream", filename=m.get("filename"))


@router.delete("/admin/email-media/{media_id}")
async def delete_email_media(media_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    m = await db.email_media.find_one({"media_id": media_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    # Refuse delete if any template still references it
    in_use = await db.email_templates.count_documents({
        "$or": [{"inline_image_id": media_id}, {"attachment_ids": media_id}]
    })
    if in_use:
        raise HTTPException(status_code=400, detail=f"Media is in use by {in_use} template(s). Detach it first.")
    p = EMAIL_MEDIA_DIR / m["stored_name"]
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
    await db.email_media.delete_one({"media_id": media_id})
    from services.email_templates import invalidate_template_cache
    invalidate_template_cache()
    return {"message": "Deleted"}
