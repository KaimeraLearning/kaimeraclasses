"""General routes: notifications, complaints, wallet, history, search, filter, renewal, learning kit"""
import os
import uuid
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Header, Form, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional

from database import db
from models.schemas import ComplaintCreate, ComplaintResolve
from services.auth import get_current_user
from services.time_utils import today_local_str

router = APIRouter()

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ── My transactions (any role) ───────────────────────────────────────────────
@router.get("/me/transactions")
async def my_transactions(request: Request, authorization: Optional[str] = Header(None)):
    """Returns the logged-in user's wallet/credit transaction history (any role).
    Each transaction is enriched with a `reference_summary` derived from related
    class / payment / proof so the user can see WHY money moved.
    """
    user = await get_current_user(request, authorization)
    txns = await db.transactions.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    # Collect reference IDs in a single round-trip
    class_ids = list({t.get("class_id") for t in txns if t.get("class_id")})
    payment_ids = list({t.get("payment_id") for t in txns if t.get("payment_id")})
    proof_ids = list({t.get("proof_id") for t in txns if t.get("proof_id")})
    counter_ids = list({t.get("counterparty_user_id") for t in txns if t.get("counterparty_user_id")})

    cls_map, pay_map, proof_map, cp_map = {}, {}, {}, {}
    if class_ids:
        for c in await db.class_sessions.find({"class_id": {"$in": class_ids}}, {"_id": 0, "class_id": 1, "title": 1, "date": 1, "subject": 1, "teacher_name": 1}).to_list(500):
            cls_map[c["class_id"]] = c
    if payment_ids:
        for p in await db.payments.find({"payment_id": {"$in": payment_ids}}, {"_id": 0, "payment_id": 1, "receipt_id": 1, "razorpay_payment_id": 1, "amount": 1, "status": 1, "type": 1}).to_list(500):
            pay_map[p["payment_id"]] = p
    if proof_ids:
        for pr in await db.class_proofs.find({"proof_id": {"$in": proof_ids}}, {"_id": 0, "proof_id": 1, "class_title": 1, "proof_date": 1, "class_id": 1}).to_list(500):
            proof_map[pr["proof_id"]] = pr
    if counter_ids:
        for u in await db.users.find({"user_id": {"$in": counter_ids}}, {"_id": 0, "user_id": 1, "name": 1, "role": 1}).to_list(500):
            cp_map[u["user_id"]] = u

    for t in txns:
        ref = {}
        if t.get("class_id") and cls_map.get(t["class_id"]):
            c = cls_map[t["class_id"]]
            ref["kind"] = "class"
            ref["label"] = f"{c.get('title','Class')} · {c.get('date','')}"
            ref["teacher_name"] = c.get("teacher_name")
        elif t.get("proof_id") and proof_map.get(t["proof_id"]):
            pr = proof_map[t["proof_id"]]
            ref["kind"] = "proof"
            ref["label"] = f"{pr.get('class_title','Class')} · session {pr.get('proof_date','')}"
            ref["class_id"] = pr.get("class_id")
        if t.get("payment_id") and pay_map.get(t["payment_id"]):
            p = pay_map[t["payment_id"]]
            ref["kind"] = ref.get("kind") or "payment"
            ref["payment_id"] = p["payment_id"]
            ref["receipt_id"] = p.get("receipt_id")
            ref["razorpay_payment_id"] = p.get("razorpay_payment_id")
        if t.get("counterparty_user_id") and cp_map.get(t["counterparty_user_id"]):
            cp = cp_map[t["counterparty_user_id"]]
            ref["counterparty_name"] = cp.get("name")
            ref["counterparty_role"] = cp.get("role")
        t["reference"] = ref
    return txns


# DIAGNOSTIC HEALTH CHECK — exposes config presence (NOT values) for deploy verification
@router.get("/health/config")
async def health_config():
    """Returns which critical env vars are loaded. Safe to expose: shows only presence + length, never values."""
    def status(key):
        v = os.environ.get(key, '')
        return {"set": bool(v), "length": len(v) if v else 0}

    def status_either(*keys):
        for k in keys:
            v = os.environ.get(k, '')
            if v:
                return {"set": True, "length": len(v), "key_used": k}
        return {"set": False, "length": 0, "key_used": None}

    # Test Gmail SMTP reachability (port 587 outbound)
    smtp_reachable = False
    smtp_error = None
    try:
        s = socket.create_connection(("smtp.gmail.com", 587), timeout=5)
        s.close()
        smtp_reachable = True
    except Exception as e:
        smtp_error = str(e)[:120]

    # Check system_pricing presence
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0, "pricing_id": 1})

    return {
        "env": {
            "MONGO_URL": status("MONGO_URL"),
            "DB_NAME": status("DB_NAME"),
            "SENDER_EMAIL": {**status_either("SENDER_EMAIL", "EMAIL_USER"), "value": os.environ.get("SENDER_EMAIL") or os.environ.get("EMAIL_USER", "")},
            "GMAIL_APP_PASSWORD": status_either("GMAIL_APP_PASSWORD", "EMAIL_PASS"),
            "ZOOM_ACCOUNT_ID": status("ZOOM_ACCOUNT_ID"),
            "ZOOM_CLIENT_ID": status("ZOOM_CLIENT_ID"),
            "ZOOM_CLIENT_SECRET": status("ZOOM_CLIENT_SECRET"),
            "ZOOM_SDK_KEY": status("ZOOM_SDK_KEY"),
            "ZOOM_SDK_SECRET": status("ZOOM_SDK_SECRET"),
            "GOOGLE_CLIENT_ID": status("GOOGLE_CLIENT_ID"),
        },
        "smtp_587_reachable": smtp_reachable,
        "smtp_error": smtp_error,
        "system_pricing_seeded": pricing is not None,
        "db_name_runtime": db.name,
    }


# NOTIFICATIONS
@router.get("/notifications/my")
async def get_my_notifications(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    notifications = await db.notifications.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return notifications

@router.post("/notifications/mark-read/{notification_id}")
async def mark_notification_read(notification_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    await db.notifications.update_one({"notification_id": notification_id, "user_id": user.user_id}, {"$set": {"read": True}})
    return {"message": "Notification marked as read"}

@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    await db.notifications.update_many({"user_id": user.user_id, "read": False}, {"$set": {"read": True}})
    return {"message": "All notifications marked as read"}


# COMPLAINTS
@router.post("/complaints/create")
async def create_complaint(complaint: ComplaintCreate, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin cannot create complaints")

    related_teacher_id = None
    if user.role == "student":
        assignment = await db.student_teacher_assignments.find_one(
            {"student_id": user.user_id, "status": {"$in": ["pending", "approved"]}}, {"_id": 0}
        )
        if assignment:
            related_teacher_id = assignment.get("teacher_id")

    complaint_id = f"complaint_{uuid.uuid4().hex[:12]}"
    complaint_doc = {
        "complaint_id": complaint_id, "raised_by": user.user_id,
        "raised_by_name": user.name, "raised_by_role": user.role,
        "related_teacher_id": related_teacher_id,
        "subject": complaint.subject, "description": complaint.description,
        "related_class_id": complaint.related_class_id,
        "status": "open", "resolution": None,
        "created_at": datetime.now(timezone.utc).isoformat(), "resolved_at": None
    }
    await db.complaints.insert_one(complaint_doc)

    if related_teacher_id:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": related_teacher_id, "type": "complaint_received",
            "title": "Student Complaint",
            "message": f"{user.name} raised a complaint: {complaint.subject}",
            "read": False, "related_id": complaint_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {"message": "Complaint submitted successfully", "complaint_id": complaint_id}

@router.get("/complaints/my")
async def get_my_complaints(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    complaints = await db.complaints.find({"raised_by": user.user_id}, {"_id": 0}).to_list(1000)
    return complaints


# WALLET
@router.get("/wallet/summary")
async def get_wallet_summary(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    transactions = await db.transactions.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)

    pending_earnings = 0
    if user.role == "teacher":
        pending_proofs = await db.class_proofs.find(
            {"teacher_id": user.user_id, "status": "verified", "admin_status": "pending"}, {"_id": 0}
        ).to_list(100)
        pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
        if pricing:
            for p in pending_proofs:
                cls = await db.class_sessions.find_one({"class_id": p.get("class_id")}, {"_id": 0})
                if cls and cls.get("is_demo"):
                    pending_earnings += pricing.get("demo_earning_teacher", 0)
                else:
                    pending_earnings += pricing.get("class_earning_teacher", 0)

    return {"balance": user.credits, "pending_earnings": pending_earnings, "bank_details": getattr(user, "bank_details", None), "transactions": transactions}


# HISTORY
@router.get("/history/search")
async def search_history(q: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    results = []
    if not q:
        return results

    regex_q = {"$regex": q, "$options": "i"}
    log_query = {"$or": [{"actor_name": regex_q}, {"actor_email": regex_q}, {"related_student_name": regex_q}, {"related_teacher_name": regex_q}, {"details": regex_q}, {"action": regex_q}]}
    logs = await db.history_logs.find(log_query, {"_id": 0}).sort("created_at", -1).to_list(100)
    results.extend(logs)

    assign_query = {"$or": [{"student_name": regex_q}, {"teacher_name": regex_q}, {"student_email": regex_q}, {"teacher_email": regex_q}]}
    assignments = await db.student_teacher_assignments.find(assign_query, {"_id": 0}).sort("assigned_at", -1).to_list(100)
    for a in assignments:
        results.append({"action": f"assignment_{a.get('status', 'unknown')}", "details": f"{a.get('student_name', '')} assigned to {a.get('teacher_name', '')} - Status: {a.get('status', '')}", "created_at": a.get("assigned_at", ""), "actor_name": a.get("student_name", ""), "related_teacher_name": a.get("teacher_name", "")})

    demo_query = {"$or": [{"student_name": regex_q}, {"email": regex_q}, {"subject": regex_q}]}
    demos = await db.demo_requests.find(demo_query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for d in demos:
        results.append({"action": f"demo_{d.get('status', 'pending')}", "details": f"Demo request by {d.get('student_name', d.get('email', ''))} - {d.get('subject', '')} - Status: {d.get('status', '')}", "created_at": d.get("created_at", ""), "actor_name": d.get("student_name", d.get("email", ""))})

    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results[:200]

@router.get("/history/student/{student_id}")
async def get_student_history(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    student = await db.users.find_one({"user_id": student_id}, {"_id": 0, "password_hash": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    demos = await db.demo_requests.find({"$or": [{"student_user_id": student_id}, {"email": student.get("email", "")}]}, {"_id": 0}).to_list(100)
    assignments = await db.student_teacher_assignments.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    classes = await db.class_sessions.find({"enrolled_students.user_id": student_id}, {"_id": 0}).to_list(100)
    complaints = await db.complaints.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    feedbacks = await db.demo_feedback.find({"student_id": student_id}, {"_id": 0}).to_list(100)
    logs = await db.history_logs.find({"$or": [{"related_student_id": student_id}, {"actor_id": student_id}]}, {"_id": 0}).sort("created_at", -1).to_list(100)

    return {"student": student, "demos": demos, "assignments": assignments, "classes": classes, "complaints": complaints, "feedbacks": feedbacks, "logs": logs}

@router.get("/history/teacher/{teacher_id}")
async def get_teacher_history(teacher_id: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")

    teacher = await db.users.find_one({"user_id": teacher_id}, {"_id": 0, "password_hash": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    demos = await db.demo_requests.find({"accepted_by_teacher_id": teacher_id}, {"_id": 0}).to_list(100)
    assignments = await db.student_teacher_assignments.find({"teacher_id": teacher_id}, {"_id": 0}).to_list(100)
    classes = await db.class_sessions.find({"teacher_id": teacher_id}, {"_id": 0}).to_list(100)
    logs = await db.history_logs.find({"$or": [{"related_teacher_id": teacher_id}, {"actor_id": teacher_id}]}, {"_id": 0}).sort("created_at", -1).to_list(100)

    return {"teacher": teacher, "demos": demos, "assignments": assignments, "classes": classes, "logs": logs}

@router.get("/history/users")
async def get_all_users_for_history(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    teachers = await db.users.find({"role": "teacher"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return {"students": students, "teachers": teachers}


# SEARCH & FILTER
@router.get("/search/teachers")
async def search_teachers(q: str = "", request: Request = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    if not q.strip():
        teachers = await db.users.find({"role": "teacher"}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(1000)
    else:
        teachers = await db.users.find(
            {"role": "teacher", "$or": [{"name": {"$regex": q, "$options": "i"}}, {"teacher_code": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]},
            {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)
    return teachers

@router.get("/filter/classes")
async def filter_classes(grade: Optional[str] = None, city: Optional[str] = None, state: Optional[str] = None, is_demo: Optional[str] = None, status: Optional[str] = None, teacher_id: Optional[str] = None, search: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
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
        query["$or"] = [{"title": {"$regex": search, "$options": "i"}}, {"class_id": {"$regex": search, "$options": "i"}}, {"subject": {"$regex": search, "$options": "i"}}, {"teacher_name": {"$regex": search, "$options": "i"}}]

    classes = await db.class_sessions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

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

@router.get("/filter/students")
async def filter_students(grade: Optional[str] = None, city: Optional[str] = None, state: Optional[str] = None, country: Optional[str] = None, search: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
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
        query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"email": {"$regex": search, "$options": "i"}}, {"institute": {"$regex": search, "$options": "i"}}]
    students = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(1000)
    return students


# RENEWAL
@router.get("/renewal/check")
async def check_renewals(request: Request, authorization: Optional[str] = Header(None)):
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
    today_str = today_local_str()
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

@router.post("/renewal/schedule-meeting")
async def schedule_renewal_meeting(class_id: str, meeting_date: str, request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    meeting_id = f"meet_{uuid.uuid4().hex[:12]}"
    student_ids = [s["user_id"] for s in cls.get("enrolled_students", [])]
    meeting_doc = {
        "meeting_id": meeting_id, "class_id": class_id, "class_title": cls.get("title", ""),
        "teacher_id": cls.get("teacher_id"), "teacher_name": cls.get("teacher_name"),
        "student_ids": student_ids, "scheduled_by": user.user_id,
        "scheduled_by_name": user.name, "meeting_date": meeting_date,
        "status": "scheduled", "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_meeting = meeting_doc.copy()
    await db.renewal_meetings.insert_one(insert_meeting)

    for sid in student_ids:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": sid, "type": "renewal_meeting", "title": "Renewal Meeting Scheduled",
            "message": f"A renewal meeting for '{cls.get('title', '')}' has been scheduled for {meeting_date} by {user.name}.",
            "read": False, "related_id": meeting_id, "created_at": datetime.now(timezone.utc).isoformat()
        })
    return {"message": "Renewal meeting scheduled", "meeting_id": meeting_id}

@router.get("/renewal/my-meetings")
async def get_my_renewal_meetings(request: Request, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    if user.role == "student":
        meetings = await db.renewal_meetings.find({"student_ids": user.user_id}, {"_id": 0}).sort("meeting_date", -1).to_list(100)
    elif user.role == "teacher":
        meetings = await db.renewal_meetings.find({"teacher_id": user.user_id}, {"_id": 0}).sort("meeting_date", -1).to_list(100)
    else:
        meetings = await db.renewal_meetings.find({}, {"_id": 0}).sort("meeting_date", -1).to_list(100)
    return meetings


# LEARNING KIT (Public endpoints)
@router.get("/learning-kit")
async def list_learning_kits(grade: Optional[str] = None, request: Request = None, authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, authorization)
    query = {}
    if grade:
        query["grade"] = grade
    elif user.role == "student":
        query["grade"] = getattr(user, "grade", None) or ""
    kits = await db.learning_kits.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return kits

@router.get("/learning-kit/download/{kit_id}")
async def download_learning_kit(kit_id: str, request: Request, authorization: Optional[str] = Header(None)):
    await get_current_user(request, authorization)
    kit = await db.learning_kits.find_one({"kit_id": kit_id}, {"_id": 0})
    if not kit:
        raise HTTPException(status_code=404, detail="Kit not found")
    file_path = UPLOADS_DIR / kit["stored_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(path=str(file_path), filename=kit["file_name"], media_type="application/octet-stream")

@router.get("/learning-kit/grades")
async def get_available_grades(request: Request, authorization: Optional[str] = Header(None)):
    await get_current_user(request, authorization)
    grades = await db.learning_kits.distinct("grade")
    return sorted(grades)
