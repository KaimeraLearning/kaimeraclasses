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
    """Counsellor/Admin views a student's attendance history, optionally filtered by class_id"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    params = dict(request.query_params)
    query = {"student_id": student_id}
    if params.get("class_id"):
        query["class_id"] = params["class_id"]

    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)

    # Also return unique classes for dropdown filter
    all_records = await db.attendance.find({"student_id": student_id}, {"_id": 0, "class_id": 1, "class_title": 1}).to_list(1000)
    classes_map = {}
    for r in all_records:
        cid = r.get("class_id")
        if cid and cid not in classes_map:
            classes_map[cid] = r.get("class_title", cid)

    return {
        "records": records,
        "classes": [{"class_id": k, "class_title": v} for k, v in classes_map.items()]
    }


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


@router.post("/counsellor/transfer-student")
async def transfer_student(data: Dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    """Transfer a student from one teacher to another mid-class. Remaining days go to new teacher."""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    student_id = data.get("student_id")
    old_teacher_id = data.get("old_teacher_id")
    new_teacher_id = data.get("new_teacher_id")

    if not student_id or not old_teacher_id or not new_teacher_id:
        raise HTTPException(status_code=400, detail="student_id, old_teacher_id, and new_teacher_id required")
    if old_teacher_id == new_teacher_id:
        raise HTTPException(status_code=400, detail="New teacher must be different from current teacher")

    # Verify new teacher exists
    new_teacher = await db.users.find_one({"user_id": new_teacher_id, "role": "teacher"}, {"_id": 0})
    if not new_teacher:
        raise HTTPException(status_code=404, detail="New teacher not found")

    # Find active assignment
    assignment = await db.student_teacher_assignments.find_one(
        {"student_id": student_id, "teacher_id": old_teacher_id, "status": "approved"},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="No active assignment found for this student-teacher pair")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find active/scheduled classes for this student with old teacher
    active_classes = await db.class_sessions.find(
        {"teacher_id": old_teacher_id, "assigned_student_id": student_id,
         "status": {"$in": ["scheduled", "in_progress"]},
         "end_date": {"$gte": today}},
        {"_id": 0}
    ).to_list(50)

    # Calculate remaining days across all classes
    total_remaining_days = 0
    for cls in active_classes:
        try:
            end_dt = datetime.strptime(cls.get("end_date", today), "%Y-%m-%d")
            today_dt = datetime.strptime(today, "%Y-%m-%d")
            remaining = max(0, (end_dt - today_dt).days + 1)
            total_remaining_days += remaining
        except ValueError:
            pass

    # Cancel old teacher's active classes (mark as transferred)
    for cls in active_classes:
        await db.class_sessions.update_one(
            {"class_id": cls["class_id"]},
            {"$set": {
                "status": "transferred",
                "transferred_to": new_teacher_id,
                "transferred_at": datetime.now(timezone.utc).isoformat(),
                "transferred_by": user.user_id
            }}
        )

    # Update old assignment as transferred
    await db.student_teacher_assignments.update_one(
        {"assignment_id": assignment["assignment_id"]},
        {"$set": {
            "status": "transferred",
            "transferred_to_teacher_id": new_teacher_id,
            "transferred_to_teacher_name": new_teacher["name"],
            "transferred_at": datetime.now(timezone.utc).isoformat(),
            "transferred_by": user.user_id
        }}
    )

    # Create new assignment for new teacher (auto-approved, already paid)
    new_assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
    student = await db.users.find_one({"user_id": student_id}, {"_id": 0})
    new_assignment_doc = {
        "assignment_id": new_assignment_id,
        "student_id": student_id,
        "student_name": student["name"] if student else assignment.get("student_name"),
        "student_email": student["email"] if student else assignment.get("student_email"),
        "teacher_id": new_teacher_id,
        "teacher_name": new_teacher["name"],
        "teacher_email": new_teacher["email"],
        "status": "approved",
        "payment_status": "paid",
        "payment_method": "transferred",
        "credit_price": assignment.get("credit_price", 0),
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "assigned_by": user.user_id,
        "learning_plan_id": assignment.get("learning_plan_id"),
        "learning_plan_name": assignment.get("learning_plan_name"),
        "learning_plan_price": assignment.get("learning_plan_price"),
        "assigned_days": total_remaining_days,
        "transferred_from_teacher_id": old_teacher_id,
        "transferred_from_assignment_id": assignment["assignment_id"]
    }
    await db.student_teacher_assignments.insert_one(new_assignment_doc)

    # Deduct rating from old teacher (admin-configured penalty)
    from services.rating import record_rating_event
    rating, suspended = await record_rating_event(
        old_teacher_id, "transfer_penalty",
        f"Student {assignment.get('student_name')} transferred to {new_teacher['name']} by counsellor"
    )

    # Notify both teachers and student
    for notif in [
        {"user_id": old_teacher_id, "type": "student_transferred_out",
         "title": "Student Transferred",
         "message": f"Student {assignment.get('student_name')} has been transferred to another teacher by counsellor."},
        {"user_id": new_teacher_id, "type": "student_transferred_in",
         "title": "New Student Assigned (Transfer)",
         "message": f"Student {assignment.get('student_name')} has been transferred to you. {total_remaining_days} days remaining."},
        {"user_id": student_id, "type": "teacher_changed",
         "title": "Your Teacher Has Changed",
         "message": f"You have been reassigned to {new_teacher['name']}. Your classes will continue shortly."}
    ]:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            **notif, "read": False, "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {
        "message": f"Student transferred to {new_teacher['name']}. {total_remaining_days} remaining days assigned.",
        "new_assignment_id": new_assignment_id,
        "old_teacher_rating": rating,
        "old_teacher_suspended": suspended
    }


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
