"""Teacher routes"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import (
    TeacherApprovalRequest, UpdateTeacherProfile, FeedbackCreate,
    ClassProofSubmit, TeacherFeedbackToStudent, TeacherDemoFeedback
)
from services.auth import get_current_user
from services.helpers import send_email
from services.rating import recalc_teacher_rating, record_rating_event

router = APIRouter()


@router.get("/teacher/dashboard")
async def teacher_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher dashboard data with session state management"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    teacher_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if teacher_doc.get("is_suspended"):
        susp_until = teacher_doc.get("suspended_until", "")
        return {
            "is_suspended": True, "suspended_until": susp_until,
            "star_rating": teacher_doc.get("star_rating", 5.0),
            "rating_details": teacher_doc.get("rating_details", {}),
            "is_approved": user.is_approved,
            "classes": [], "other_classes": [], "todays_sessions": [],
            "upcoming_classes": [], "conducted_classes": [],
            "pending_assignments": [], "approved_students": []
        }

    all_classes = await db.class_sessions.find({"teacher_id": user.user_id}, {"_id": 0}).to_list(1000)
    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')

    todays_sessions = []
    upcoming_classes = []
    conducted_classes = []
    cancelled_classes = []

    for cls in all_classes:
        cls_date = cls.get('date', '')
        cls_end_date = cls.get('end_date', cls_date)
        status = cls.get('status', 'scheduled')

        if status in ('cancelled',):
            cancelled_classes.append(cls)
        elif status == 'completed':
            conducted_classes.append(cls)
        elif cls_end_date < today_str:
            # Past end date - auto-complete
            await db.class_sessions.update_one({"class_id": cls['class_id']}, {"$set": {"status": "completed"}})
            cls['status'] = 'completed'
            # Mark demo request as completed if this is a demo class
            if cls.get('is_demo'):
                sid = cls.get('assigned_student_id')
                tid = cls.get('teacher_id')
                if sid and tid:
                    await db.demo_requests.update_many(
                        {"$or": [{"student_user_id": sid}, {"student_id": sid}],
                         "accepted_by_teacher_id": tid, "status": "accepted"},
                        {"$set": {"status": "completed", "completed_at": now.isoformat()}}
                    )
            conducted_classes.append(cls)
        elif cls_date == today_str or (cls_date <= today_str and cls_end_date >= today_str):
            # Check if today's session time has passed
            end_time_str = cls.get('end_time', '23:59')
            try:
                end_time = datetime.strptime(f"{today_str} {end_time_str}", '%Y-%m-%d %H:%M')
                end_time = end_time.replace(tzinfo=timezone.utc)
                if now > end_time and status in ('scheduled', 'in_progress'):
                    # Time passed today - show in conducted for proof submission
                    if cls_end_date == today_str:
                        await db.class_sessions.update_one({"class_id": cls['class_id']}, {"$set": {"status": "completed"}})
                        cls['status'] = 'completed'
                        # Mark demo request as completed if demo class
                        if cls.get('is_demo'):
                            sid = cls.get('assigned_student_id')
                            tid = cls.get('teacher_id')
                            if sid and tid:
                                await db.demo_requests.update_many(
                                    {"$or": [{"student_user_id": sid}, {"student_id": sid}],
                                     "accepted_by_teacher_id": tid, "status": "accepted"},
                                    {"$set": {"status": "completed", "completed_at": now.isoformat()}}
                                )
                    conducted_classes.append(cls)
                else:
                    todays_sessions.append(cls)
            except (ValueError, TypeError):
                todays_sessions.append(cls)
        elif cls_date > today_str and status in ('scheduled', 'in_progress'):
            upcoming_classes.append(cls)
        else:
            conducted_classes.append(cls)

    pending_assignments = await db.student_teacher_assignments.find(
        {"teacher_id": user.user_id, "status": "pending"}, {"_id": 0}
    ).to_list(1000)
    approved_students = await db.student_teacher_assignments.find(
        {"teacher_id": user.user_id, "status": "approved", "payment_status": "paid"}, {"_id": 0}
    ).to_list(1000)
    awaiting_payment = await db.student_teacher_assignments.find(
        {"teacher_id": user.user_id, "status": "approved", "payment_status": {"$ne": "paid"}}, {"_id": 0}
    ).to_list(1000)

    # Enrich assignments with counselor name
    counselor_ids = set()
    for a in pending_assignments + approved_students + awaiting_payment:
        if a.get("assigned_by"):
            counselor_ids.add(a["assigned_by"])
    if counselor_ids:
        counselors = await db.users.find(
            {"user_id": {"$in": list(counselor_ids)}},
            {"_id": 0, "user_id": 1, "name": 1}
        ).to_list(100)
        counselor_map = {c["user_id"]: c["name"] for c in counselors}
        for a in pending_assignments + approved_students + awaiting_payment:
            if a.get("assigned_by"):
                a["counselor_name"] = counselor_map.get(a["assigned_by"], "")
                a["counselor_id"] = a["assigned_by"]

    # Check proof submission status for conducted classes AND today's ended sessions
    all_check_classes = conducted_classes + [c for c in todays_sessions if c.get('status') in ('completed', 'scheduled')]
    class_ids = [c['class_id'] for c in all_check_classes]
    today_str_proof = now.strftime('%Y-%m-%d')
    if class_ids:
        # Get all proofs for these classes
        proofs = await db.class_proofs.find(
            {"class_id": {"$in": class_ids}}, {"_id": 0, "class_id": 1, "proof_date": 1}
        ).to_list(5000)
        # For multi-day classes: check if TODAY's proof is submitted
        # For single-day classes: check if any proof exists
        for cls in all_check_classes:
            cls_proofs = [p for p in proofs if p['class_id'] == cls['class_id']]
            if cls.get('duration_days', 1) > 1:
                # Multi-day: proof needed per day
                today_proof = any(p.get('proof_date') == today_str_proof for p in cls_proofs)
                cls['proof_submitted'] = today_proof
                cls['total_proofs'] = len(cls_proofs)
            else:
                cls['proof_submitted'] = len(cls_proofs) > 0

    return {
        "is_approved": user.is_approved, "is_suspended": False,
        "star_rating": teacher_doc.get("star_rating", 5.0),
        "rating_details": teacher_doc.get("rating_details", {}),
        "classes": todays_sessions, "other_classes": upcoming_classes + conducted_classes,
        "todays_sessions": todays_sessions, "upcoming_classes": upcoming_classes,
        "conducted_classes": conducted_classes,
        "cancelled_classes": cancelled_classes,
        "pending_assignments": pending_assignments, "approved_students": approved_students,
        "awaiting_payment": awaiting_payment
    }


@router.post("/teacher/approve-assignment")
async def approve_student_assignment(
    approval: TeacherApprovalRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Teacher approves or rejects student assignment"""

    user = await get_current_user(request, authorization)

    # ✅ Only teacher allowed
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    # ✅ Fetch assignment
    assignment = await db.student_teacher_assignments.find_one(
        {"assignment_id": approval.assignment_id},
        {"_id": 0}
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # ✅ Check ownership
    if assignment["teacher_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    # ✅ Already processed
    if assignment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Assignment already processed")

    # ✅ Expiry check
    expires_at = datetime.fromisoformat(assignment["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        await db.student_teacher_assignments.update_one(
            {"assignment_id": approval.assignment_id},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Assignment expired")

    # =========================
    # ✅ APPROVE FLOW
    # =========================
    if approval.approved:
        await db.student_teacher_assignments.update_one(
            {"assignment_id": approval.assignment_id},
            {
                "$set": {
                    "status": "approved",
                    "payment_status": "pending",
                    "approved_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        # 🔔 Notify student
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": assignment["student_id"],
            "type": "assignment_approved",
            "title": "Teacher Accepted!",
            "message": f"Teacher {user.name} has accepted your enrollment. Classes will be charged when scheduled.",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        action = "approved"

    # =========================
    # ❌ REJECT FLOW
    # =========================
    else:
        await db.student_teacher_assignments.update_one(
            {"assignment_id": approval.assignment_id},
            {
                "$set": {
                    "status": "rejected",
                    "approved_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        action = "rejected"

    # ✅ Final response
    return {"message": f"Student assignment {action}"}

@router.post("/teacher/cancel-class/{class_id}")
async def teacher_cancel_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher cancels a class - impacts their rating"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    if cls.get('status') == 'completed':
        raise HTTPException(status_code=400, detail="Cannot cancel completed class")
    if cls.get('status') == 'cancelled':
        raise HTTPException(status_code=400, detail="This class is already cancelled")

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {
            "status": "cancelled", "cancelled_by": "teacher",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "can_reschedule": True
        }}
    )

    student_id = cls.get("assigned_student_id")
    refund = cls.get("credits_required", 0)
    if student_id and refund > 0:
        await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": refund}})
        await db.transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": student_id, "type": "teacher_cancel_refund", "amount": refund,
            "description": f"Refund: Teacher cancelled '{cls['title']}'",
            "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
        })

    rating, suspended = await record_rating_event(user.user_id, "cancellation", f"Cancelled class {cls['title']}")

    if student_id:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": student_id, "type": "teacher_cancelled",
            "title": "Class Cancelled by Teacher",
            "message": f"Teacher {user.name} cancelled '{cls['title']}'. Credits refunded.",
            "read": False, "created_at": datetime.now(timezone.utc).isoformat()
        })

        # Check if ALL classes for this student-teacher assignment are now cancelled
        # If so, refund the Razorpay assignment payment to student wallet
        remaining_active = await db.class_sessions.find_one(
            {"teacher_id": user.user_id, "assigned_student_id": student_id,
             "status": {"$nin": ["cancelled"]}},
            {"_id": 0}
        )
        if not remaining_active:
            assignment = await db.student_teacher_assignments.find_one(
                {"teacher_id": user.user_id, "student_id": student_id, "status": "approved"},
                {"_id": 0}
            )
            if assignment and assignment.get("payment_status") == "paid":
                plan_price = assignment.get("learning_plan_price") or assignment.get("credit_price", 0)
                if plan_price > 0:
                    await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": plan_price}})
                    await db.transactions.insert_one({
                        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                        "user_id": student_id, "type": "full_cancellation_refund",
                        "amount": plan_price,
                        "description": f"Full refund: All classes cancelled by teacher. Assignment payment refunded to wallet.",
                        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    await db.student_teacher_assignments.update_one(
                        {"assignment_id": assignment["assignment_id"]},
                        {"$set": {"payment_status": "refunded", "refunded_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    await db.notifications.insert_one({
                        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                        "user_id": student_id, "type": "payment_refunded",
                        "title": "Payment Refunded",
                        "message": f"All your classes with {user.name} were cancelled. Your payment of Rs.{plan_price} has been refunded to your wallet.",
                        "read": False, "created_at": datetime.now(timezone.utc).isoformat()
                    })

    msg = f"Class cancelled. Your rating is now {rating}."
    if suspended:
        msg += " WARNING: Your account has been suspended for 3 days due to excessive cancellations."
    return {"message": msg, "star_rating": rating, "is_suspended": suspended}


@router.get("/teacher/my-rating")
async def teacher_my_rating(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher views their own rating and negative markings"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    teacher_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "star_rating": 1, "rating_details": 1, "is_suspended": 1, "suspended_until": 1, "monthly_cancellations": 1})
    events = await db.teacher_rating_events.find(
        {"teacher_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    return {
        "star_rating": teacher_doc.get("star_rating", 5.0),
        "is_suspended": teacher_doc.get("is_suspended", False),
        "suspended_until": teacher_doc.get("suspended_until"),
        "rating_details": teacher_doc.get("rating_details", {}),
        "recent_events": events
    }


@router.post("/feedback/submit")
async def submit_feedback(feedback_data: FeedbackCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Submit feedback for a student"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    cls = await db.class_sessions.find_one({"class_id": feedback_data.class_id}, {"_id": 0})
    if not cls or cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    student = await db.users.find_one({"user_id": feedback_data.student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    feedback_id = f"feedback_{uuid.uuid4().hex[:12]}"
    feedback_doc = {
        "feedback_id": feedback_id, "class_id": feedback_data.class_id,
        "student_id": feedback_data.student_id, "student_name": student['name'],
        "teacher_id": user.user_id, "rating": feedback_data.rating,
        "comments": feedback_data.comments, "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.feedback.insert_one(feedback_doc)
    return {"message": "Feedback submitted successfully"}


@router.post("/teacher/update-profile")
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
        await db.users.update_one({"user_id": user.user_id}, {"$set": update_fields})
    return {"message": "Profile updated successfully"}


@router.post("/teacher/submit-proof")
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

    existing = await db.class_proofs.find_one({"class_id": proof.class_id}, {"_id": 0})
    if existing:
        # For multi-day classes, check if proof already submitted today
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if cls.get("duration_days", 1) > 1:
            existing_today = await db.class_proofs.find_one(
                {"class_id": proof.class_id, "proof_date": today_str}, {"_id": 0}
            )
            if existing_today:
                raise HTTPException(status_code=400, detail="Proof already submitted for today's session")
        else:
            raise HTTPException(status_code=400, detail="Proof already submitted for this class")

    proof_id = f"proof_{uuid.uuid4().hex[:12]}"
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    proof_doc = {
        "proof_id": proof_id, "class_id": proof.class_id, "class_title": cls['title'],
        "teacher_id": user.user_id, "teacher_name": user.name,
        "student_id": cls.get('assigned_student_id', ''),
        "feedback_text": proof.feedback_text, "student_performance": proof.student_performance,
        "topics_covered": proof.topics_covered, "screenshot_base64": proof.screenshot_base64,
        "status": "pending", "submitted_at": datetime.now(timezone.utc).isoformat(),
        "proof_date": today_str,
        "reviewed_by": None, "reviewed_at": None, "reviewer_notes": None
    }
    await db.class_proofs.insert_one(proof_doc)
    await db.class_sessions.update_one({"class_id": proof.class_id}, {"$set": {"verification_status": "submitted"}})

    return {"message": "Proof submitted successfully", "proof_id": proof_id}


@router.get("/teacher/my-proofs")
async def get_teacher_proofs(request: Request, authorization: Optional[str] = Header(None)):
    """Get all proofs submitted by this teacher"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    proofs = await db.class_proofs.find(
        {"teacher_id": user.user_id}, {"_id": 0, "screenshot_base64": 0}
    ).to_list(1000)
    return proofs


@router.post("/teacher/feedback-to-student")
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
        "feedback_id": feedback_id, "teacher_id": user.user_id, "teacher_name": user.name,
        "student_id": data.student_id, "student_name": student["name"],
        "class_id": data.class_id, "feedback_text": data.feedback_text,
        "performance_rating": data.performance_rating,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_fb = feedback_doc.copy()
    await db.teacher_student_feedback.insert_one(insert_fb)

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": data.student_id, "type": "teacher_feedback",
        "title": f"Feedback from {user.name}",
        "message": f"Performance: {data.performance_rating.replace('_', ' ').title()}. {data.feedback_text}",
        "read": False, "related_id": feedback_id, "created_at": datetime.now(timezone.utc).isoformat()
    })

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


@router.post("/teacher/submit-demo-feedback")
async def teacher_submit_demo_feedback(data: TeacherDemoFeedback, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher submits mandatory demo feedback - auto-notifies counsellor"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    demo = await db.demo_requests.find_one({"demo_id": data.demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")

    existing = await db.teacher_student_feedback.find_one(
        {"teacher_id": user.user_id, "demo_id": data.demo_id, "type": "demo_feedback"}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Demo feedback already submitted")

    feedback_id = f"tdf_{uuid.uuid4().hex[:12]}"
    feedback_doc = {
        "feedback_id": feedback_id, "type": "demo_feedback", "demo_id": data.demo_id,
        "teacher_id": user.user_id, "teacher_name": user.name,
        "teacher_code": getattr(user, 'teacher_code', ''),
        "student_id": data.student_id, "feedback_text": data.feedback_text,
        "performance_rating": data.performance_rating,
        "recommended_frequency": data.recommended_frequency,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_doc = feedback_doc.copy()
    await db.teacher_student_feedback.insert_one(insert_doc)

    await db.demo_requests.update_one(
        {"demo_id": data.demo_id},
        {"$set": {
            "teacher_feedback_submitted": True, "teacher_feedback_id": feedback_id,
            "teacher_feedback_rating": data.performance_rating, "teacher_feedback_text": data.feedback_text
        }}
    )

    counsellors = await db.users.find({"role": "counsellor"}, {"_id": 0}).to_list(100)
    student = await db.users.find_one({"user_id": data.student_id}, {"_id": 0, "name": 1, "email": 1})
    student_name = student.get("name", "Student") if student else "Student"
    for c in counsellors:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": c["user_id"], "type": "teacher_demo_feedback",
            "title": "Teacher Demo Feedback Submitted",
            "message": f"Teacher {user.name} rated {student_name}'s demo as '{data.performance_rating}': {data.feedback_text[:100]}",
            "read": False, "related_id": data.demo_id, "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {"message": "Demo feedback submitted and counsellors notified"}


@router.get("/teacher/pending-demo-feedback")
async def teacher_pending_demo_feedback(request: Request, authorization: Optional[str] = Header(None)):
    """Get demos awaiting teacher feedback"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    demos = await db.demo_requests.find(
        {"accepted_by_teacher_id": user.user_id, "status": {"$in": ["completed", "feedback_submitted"]},
         "$or": [{"teacher_feedback_submitted": {"$exists": False}}, {"teacher_feedback_submitted": False}]},
        {"_id": 0}
    ).to_list(50)
    return demos


@router.get("/teacher/student-complaints")
async def get_teacher_student_complaints(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher sees complaints from their assigned students"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    complaints = await db.complaints.find({"related_teacher_id": user.user_id}, {"_id": 0}).to_list(1000)
    return complaints


@router.post("/teacher/calendar")
async def add_calendar_entry(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher adds a content plan entry to their calendar"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    body = await request.json()
    entry_id = f"cal_{uuid.uuid4().hex[:12]}"
    entry_doc = {
        "entry_id": entry_id, "teacher_id": user.user_id, "teacher_name": user.name,
        "date": body.get("date"), "title": body.get("title", ""),
        "description": body.get("description", ""), "subject": body.get("subject", ""),
        "color": body.get("color", "#0ea5e9"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_entry = entry_doc.copy()
    await db.teacher_calendar.insert_one(insert_entry)
    return {"message": "Calendar entry added", "entry_id": entry_id}


@router.get("/teacher/calendar")
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


@router.delete("/teacher/calendar/{entry_id}")
async def delete_calendar_entry(entry_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher removes a calendar entry"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    result = await db.teacher_calendar.delete_one({"entry_id": entry_id, "teacher_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Calendar entry deleted"}


@router.get("/teacher/grouped-classes")
async def get_teacher_grouped_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher's classes grouped by student, with today's classes separate"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    all_classes = await db.class_sessions.find(
        {"teacher_id": user.user_id}, {"_id": 0}
    ).sort("date", -1).to_list(1000)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_classes = []
    active_by_student = {}
    ended_classes = []

    for cls in all_classes:
        start_date = cls.get("date", "")
        end_date = cls.get("end_date", start_date)

        if end_date < today_str and cls.get("status") not in ["in_progress"]:
            cls["display_status"] = "ended"
            ended_classes.append(cls)
            continue

        if start_date <= today_str <= end_date:
            cls["is_today"] = True
            today_classes.append(cls)

        for student in cls.get("enrolled_students", []):
            sid = student.get("user_id", "unknown")
            sname = student.get("name", "Unknown Student")
            if sid not in active_by_student:
                active_by_student[sid] = {"student_id": sid, "student_name": sname, "classes": []}
            active_by_student[sid]["classes"].append(cls)

    for sid in active_by_student:
        student = await db.users.find_one({"user_id": sid}, {"_id": 0, "password_hash": 0})
        if student:
            active_by_student[sid]["student_details"] = student

    return {"today": today_classes, "by_student": list(active_by_student.values()), "ended_count": len(ended_classes)}


@router.get("/teacher/schedule")
async def get_teacher_schedule(request: Request, authorization: Optional[str] = Header(None)):
    """Get teacher's full schedule for schedule planner view"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    classes = await db.class_sessions.find(
        {"teacher_id": user.user_id, "status": {"$in": ["scheduled", "in_progress"]}}, {"_id": 0}
    ).sort("date", 1).to_list(500)
    return classes


@router.post("/teacher/reschedule-class/{class_id}")
async def reschedule_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher reschedules a class - works for student-cancelled sessions and teacher-cancelled classes"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teachers only")

    body = await request.json()
    new_date = body.get("new_date")
    new_start_time = body.get("new_start_time")
    new_end_time = body.get("new_end_time")

    if not new_date or not new_start_time or not new_end_time:
        raise HTTPException(status_code=400, detail="New date, start_time, and end_time required")

    cls = await db.class_sessions.find_one({"class_id": class_id, "teacher_id": user.user_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Allow reschedule if: student cancelled today's session OR teacher cancelled the class
    is_teacher_cancelled = cls.get("status") == "cancelled" and cls.get("cancelled_by") == "teacher"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    student_cancelled_today = any(c.get("date") == today for c in (cls.get("cancellations") or []))

    if not is_teacher_cancelled and not student_cancelled_today:
        raise HTTPException(status_code=400, detail="Can only reschedule cancelled classes or student-cancelled sessions")

    update_fields = {
        "rescheduled": True, "rescheduled_date": new_date,
        "rescheduled_start_time": new_start_time, "rescheduled_end_time": new_end_time,
        "rescheduled_at": datetime.now(timezone.utc).isoformat(), "cancelled_today": False,
        "reschedule_count": (cls.get("reschedule_count", 0) + 1)
    }

    # If teacher cancelled the whole class, reactivate it with new schedule
    if is_teacher_cancelled:
        update_fields["status"] = "scheduled"
        update_fields["date"] = new_date
        update_fields["start_time"] = new_start_time
        update_fields["end_time"] = new_end_time
        # Shift end_date by 1 day for this reschedule
        end_date = datetime.fromisoformat(new_date) + timedelta(days=cls.get("duration_days", 1) - 1 + 1)
        update_fields["end_date"] = end_date.isoformat().split('T')[0]
        update_fields["can_reschedule"] = False

        # Reclaim the per-class credit refund that was given on cancel
        student_id = cls.get("assigned_student_id")
        refund_to_reclaim = cls.get("credits_required", 0)
        if student_id and refund_to_reclaim > 0:
            await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": -refund_to_reclaim}})
            await db.transactions.insert_one({
                "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                "user_id": student_id, "type": "reschedule_recharge",
                "amount": -refund_to_reclaim,
                "description": f"Re-charged: Class '{cls['title']}' rescheduled by teacher (refund reversed)",
                "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
            })

        # If full assignment refund was issued, reverse it too
        if student_id:
            assignment = await db.student_teacher_assignments.find_one(
                {"teacher_id": user.user_id, "student_id": student_id, "status": "approved", "payment_status": "refunded"},
                {"_id": 0}
            )
            if assignment:
                plan_price = assignment.get("learning_plan_price") or assignment.get("credit_price", 0)
                if plan_price > 0:
                    await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": -plan_price}})
                    await db.transactions.insert_one({
                        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                        "user_id": student_id, "type": "refund_reversal",
                        "amount": -plan_price,
                        "description": f"Refund reversed: Teacher rescheduled class. Assignment payment re-applied.",
                        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    await db.student_teacher_assignments.update_one(
                        {"assignment_id": assignment["assignment_id"]},
                        {"$set": {"payment_status": "paid", "refunded_at": None}}
                    )

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": update_fields}
    )

    for s in cls.get("enrolled_students", []):
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": s["user_id"], "type": "class_rescheduled",
            "title": "Class Rescheduled",
            "message": f"Your class '{cls['title']}' has been rescheduled to {new_date} at {new_start_time}-{new_end_time}",
            "read": False, "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {"message": "Class rescheduled successfully"}



# ── PROFILE MANAGEMENT ──

@router.get("/teacher/profile")
async def get_teacher_profile(request: Request, authorization: Optional[str] = Header(None)):
    """Get full teacher profile"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "password_hash": 0})
    return doc


@router.post("/teacher/update-full-profile")
async def update_teacher_full_profile(request: Request, authorization: Optional[str] = Header(None)):
    """Update teacher profile fields (bank details locked after first entry)"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    body = await request.json()
    current = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})

    editable = ["bio", "age", "date_of_birth", "address", "education_qualification",
                 "interests_hobbies", "teaching_experience", "profile_picture", "klat_score"]
    updates = {}
    for field in editable:
        if field in body and body[field] is not None:
            updates[field] = body[field]

    # Bank details: can only be set once by teacher, then locked
    bank_fields = ["bank_name", "bank_account_number", "bank_ifsc_code"]
    existing_bank = current.get("bank_name")
    if not existing_bank:
        for bf in bank_fields:
            if bf in body and body[bf]:
                updates[bf] = body[bf]
    else:
        # Bank already set - teacher cannot change
        for bf in bank_fields:
            if bf in body and body[bf] and body[bf] != current.get(bf):
                raise HTTPException(status_code=403, detail="Bank details are locked. Only admin can update them.")

    if updates:
        await db.users.update_one({"user_id": user.user_id}, {"$set": updates})
    return {"message": "Profile updated successfully", "updated_fields": list(updates.keys())}


@router.post("/teacher/upload-resume")
async def upload_teacher_resume(request: Request, authorization: Optional[str] = Header(None)):
    """Upload PDF resume as base64"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    body = await request.json()
    resume_data = body.get("resume_base64")
    resume_name = body.get("resume_name", "resume.pdf")
    if not resume_data:
        raise HTTPException(status_code=400, detail="No resume data provided")
    await db.users.update_one({"user_id": user.user_id}, {"$set": {
        "resume_base64": resume_data, "resume_name": resume_name
    }})
    return {"message": "Resume uploaded successfully"}


@router.get("/teacher/view-profile/{teacher_id}")
async def view_teacher_profile(teacher_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """View teacher profile - accessible by admin, counselor, students assigned to teacher"""
    user = await get_current_user(request, authorization)
    doc = await db.users.find_one({"user_id": teacher_id, "role": "teacher"}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Remove bank details for non-admin users
    if user.role != "admin":
        doc.pop("bank_name", None)
        doc.pop("bank_account_number", None)
        doc.pop("bank_ifsc_code", None)

    return doc
