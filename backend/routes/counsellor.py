"""Counsellor routes"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional, Dict, Any

from database import db
from models.schemas import ProofVerification
from services.auth import get_current_user

router = APIRouter()


@router.get("/counsellor/dashboard")
async def counsellor_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get counsellor dashboard data"""
    user = await get_current_user(request, authorization)
    if user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counsellor access only")

    all_students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    active_assignments = await db.student_teacher_assignments.find(
        {"status": {"$in": ["pending", "approved"]}}, {"_id": 0}
    ).to_list(1000)
    rejected_assignments = await db.student_teacher_assignments.find({"status": "rejected"}, {"_id": 0}).to_list(1000)

    assigned_student_ids = set([a['student_id'] for a in active_assignments])
    unassigned_students = [s for s in all_students if s['user_id'] not in assigned_student_ids]

    for student in unassigned_students:
        demo = await db.demo_requests.find_one(
            {"student_id": student["user_id"], "status": {"$in": ["accepted", "completed", "feedback_submitted"]}},
            {"_id": 0, "accepted_by_teacher_name": 1, "teacher_feedback_text": 1, "teacher_feedback_rating": 1}
        )
        if demo:
            student["demo_teacher_name"] = demo.get("accepted_by_teacher_name")
            student["demo_feedback_text"] = demo.get("teacher_feedback_text")
            student["demo_feedback_rating"] = demo.get("teacher_feedback_rating")

    teachers = await db.users.find({"role": "teacher", "is_approved": True}, {"_id": 0, "password_hash": 0}).to_list(1000)

    return {
        "unassigned_students": unassigned_students,
        "all_students": all_students,
        "teachers": teachers,
        "active_assignments": active_assignments,
        "rejected_assignments": rejected_assignments
    }


@router.get("/counsellor/student-profile/{student_id}")
async def get_student_profile(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get detailed student profile for counsellor view"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    student = await db.users.find_one({"user_id": student_id, "role": "student"}, {"_id": 0, "password_hash": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assignment = await db.student_teacher_assignments.find_one(
        {"student_id": student_id, "status": {"$in": ["pending", "approved"]}}, {"_id": 0}
    )
    classes = await db.class_sessions.find({"enrolled_students.user_id": student_id}, {"_id": 0}).to_list(100)

    demos = await db.demo_requests.find({"student_id": student_id}, {"_id": 0}).sort("created_at", -1).to_list(20)
    demo_history = []
    for d in demos:
        demo_history.append({
            "demo_id": d.get("demo_id"), "title": d.get("subject", "Demo Session"),
            "date": d.get("preferred_date"), "status": d.get("status"),
            "teacher_name": d.get("accepted_by_teacher_name"),
            "teacher_id": d.get("accepted_by_teacher_id")
        })

    return {"student": student, "current_assignment": assignment, "class_history": classes, "demo_history": demo_history}


@router.get("/counsellor/student-attendance/{student_id}")
async def counsellor_student_attendance(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor views a student's full attendance history including off-day markings"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    records = await db.attendance.find({"student_id": student_id}, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@router.get("/counsellor/pending-proofs")
async def get_pending_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all pending class proofs for counsellor verification"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    proofs = await db.class_proofs.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    return proofs


@router.get("/counsellor/all-proofs")
async def get_all_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all class proofs"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")
    proofs = await db.class_proofs.find({}, {"_id": 0}).to_list(1000)
    return proofs


@router.post("/counsellor/verify-proof")
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
        "status": new_status, "reviewed_by": user.user_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_notes": verification.reviewer_notes
    }
    if verification.approved:
        update_data["admin_status"] = "pending"

    await db.class_proofs.update_one({"proof_id": verification.proof_id}, {"$set": update_data})
    await db.class_sessions.update_one({"class_id": proof['class_id']}, {"$set": {"verification_status": new_status}})

    if verification.approved:
        admins = await db.users.find({"role": "admin"}, {"_id": 0}).to_list(10)
        for admin in admins:
            await db.notifications.insert_one({
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": admin["user_id"], "type": "proof_for_admin_review",
                "title": "Proof Awaiting Your Approval",
                "message": f"Counsellor {user.name} approved proof for class '{proof.get('class_title', '')}'. Credit pending your approval.",
                "read": False, "related_id": verification.proof_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

    action = "approved (forwarded to Admin)" if verification.approved else "rejected"
    return {"message": f"Proof {action} successfully"}


@router.get("/counsellor/expired-classes")
async def get_expired_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Get classes whose duration has ended for reassignment decisions"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')
    all_classes = await db.class_sessions.find({"status": "scheduled"}, {"_id": 0}).to_list(10000)

    expired_classes = []
    for cls in all_classes:
        end_date_str = cls.get('end_date', cls['date'])
        if end_date_str < today_str:
            end_date = datetime.fromisoformat(end_date_str)
            days_since = (now - end_date.replace(tzinfo=timezone.utc)).days
            cls['days_since_expiry'] = days_since
            cls['can_rebook'] = days_since <= 3
            expired_classes.append(cls)
    return expired_classes


@router.post("/counsellor/reassign-student")
async def reassign_student(data: Dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor reassigns or releases a student after class duration ends"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    student_id = data.get('student_id')
    action = data.get('action')

    if action == "release":
        await db.student_teacher_assignments.update_many(
            {"student_id": student_id, "status": "approved"}, {"$set": {"status": "completed"}}
        )
        return {"message": "Student released for reassignment"}
    elif action == "rebook":
        return {"message": "Student kept with current teacher for rebooking"}

    raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/counsellor/search-students")
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
            ]}, {"_id": 0, "password_hash": 0}
        ).sort("name", 1).to_list(1000)
    else:
        students = await db.users.find({"role": "student"}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(1000)
    return students



# ── COUNSELOR PROFILE MANAGEMENT ──

@router.get("/counsellor/profile")
async def get_counselor_profile(request: Request, authorization: Optional[str] = Header(None)):
    """Get full counselor profile"""
    user = await get_current_user(request, authorization)
    if user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counselor access only")
    doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "password_hash": 0})
    return doc


@router.post("/counsellor/update-full-profile")
async def update_counselor_full_profile(request: Request, authorization: Optional[str] = Header(None)):
    """Update counselor profile fields (bank details locked after first entry)"""
    user = await get_current_user(request, authorization)
    if user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counselor access only")
    body = await request.json()
    current = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})

    editable = ["bio", "age", "date_of_birth", "address", "education_qualification",
                 "interests_hobbies", "experience", "profile_picture", "klcat_score"]
    updates = {}
    for field in editable:
        if field in body and body[field] is not None:
            updates[field] = body[field]

    # Bank details: can only be set once, then locked
    bank_fields = ["bank_name", "bank_account_number", "bank_ifsc_code"]
    existing_bank = current.get("bank_name")
    if not existing_bank:
        for bf in bank_fields:
            if bf in body and body[bf]:
                updates[bf] = body[bf]
    else:
        for bf in bank_fields:
            if bf in body and body[bf] and body[bf] != current.get(bf):
                raise HTTPException(status_code=403, detail="Bank details are locked. Only admin can update them.")

    if updates:
        await db.users.update_one({"user_id": user.user_id}, {"$set": updates})
    return {"message": "Profile updated successfully", "updated_fields": list(updates.keys())}


@router.post("/counsellor/upload-resume")
async def upload_counselor_resume(request: Request, authorization: Optional[str] = Header(None)):
    """Upload PDF resume as base64"""
    user = await get_current_user(request, authorization)
    if user.role != "counsellor":
        raise HTTPException(status_code=403, detail="Counselor access only")
    body = await request.json()
    resume_data = body.get("resume_base64")
    resume_name = body.get("resume_name", "resume.pdf")
    if not resume_data:
        raise HTTPException(status_code=400, detail="No resume data provided")
    await db.users.update_one({"user_id": user.user_id}, {"$set": {
        "resume_base64": resume_data, "resume_name": resume_name
    }})
    return {"message": "Resume uploaded successfully"}


@router.get("/counsellor/view-profile/{counselor_id}")
async def view_counselor_profile(counselor_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """View counselor profile - accessible by admin, students"""
    user = await get_current_user(request, authorization)
    doc = await db.users.find_one({"user_id": counselor_id, "role": "counsellor"}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Counselor not found")

    # Remove bank details for non-admin users
    if user.role != "admin":
        doc.pop("bank_name", None)
        doc.pop("bank_account_number", None)
        doc.pop("bank_ifsc_code", None)

    return doc
