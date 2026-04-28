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
from services.helpers import generate_teacher_code, generate_student_code, send_email, generate_otp, insert_admin_mirror_txn, notify_event, generate_temp_password

router = APIRouter()


def validate_gmail(email: str):
    """Enforce @gmail.com only for manual user creation"""
    if not email.lower().endswith('@gmail.com'):
        raise HTTPException(status_code=400, detail="Only @gmail.com email addresses are allowed")

UPLOADS_DIR = Path("/app/backend/uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


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
        cta_url="https://edu.kaimeralearning.com/student-dashboard"
    )
    await notify_event(
        teacher.get('email'),
        f"New Class Request — Student {student['name']}",
        "You have a new class request",
        f"<b>{student['name']}</b> has been assigned to you for the <b>{plan_label}</b> ({days_label}). Please review and accept within 24 hours from your teacher dashboard.",
        cta_label="Review Request",
        cta_url="https://edu.kaimeralearning.com/teacher-dashboard"
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
        cta_url="https://edu.kaimeralearning.com/login"
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
        cta_url="https://edu.kaimeralearning.com/login"
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
        cta_url="https://edu.kaimeralearning.com/login"
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
        cta_url="https://edu.kaimeralearning.com/login"
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
        cta_url="https://edu.kaimeralearning.com/login"
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
