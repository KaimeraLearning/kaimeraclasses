"""Student routes"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import StudentProfileUpdate, StudentFeedbackRating
from services.auth import get_current_user
from services.rating import recalc_teacher_rating, record_rating_event

router = APIRouter()


@router.get("/student/dashboard")
async def student_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    """Get student dashboard data with live/upcoming/completed sections"""
    user = await get_current_user(request, authorization)

    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    # Get all classes where student is enrolled
    all_classes = await db.class_sessions.find(
        {"enrolled_students.user_id": user.user_id},
        {"_id": 0}
    ).to_list(1000)

    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')

    live_classes = []
    upcoming = []
    completed = []
    pending_rating = []
    cancelled = []

    def _annotate_no_show(c):
        """Mark class as teacher_no_show if scheduled end has passed and the
        teacher never started it (`started_at_actual` is null). Computed on the
        fly so the banner appears automatically — no cron needed."""
        if c.get("started_at_actual"):
            c["teacher_no_show"] = False
            return
        end_t = (c.get("end_time") or "23:59")
        try:
            end_dt = datetime.fromisoformat(f"{c.get('end_date') or c.get('date')}T{end_t}:00")
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
        except Exception:
            c["teacher_no_show"] = False
            return
        # 30 minute grace after scheduled end before declaring no-show
        c["teacher_no_show"] = now > end_dt + timedelta(minutes=30)

    for cls in all_classes:
        status = cls.get('status', 'scheduled')
        cls_date = cls.get('date', '')
        cls_end_date = cls.get('end_date', cls_date)

        if status == 'cancelled' or status == 'cancelled_by_teacher':
            cancelled.append(cls)
        elif status == 'in_progress' or (status == 'scheduled' and cls_date == today_str):
            _annotate_no_show(cls)
            live_classes.append(cls)
        elif status == 'completed':
            # Check if student has rated it
            rated = await db.feedback.find_one(
                {"class_id": cls["class_id"], "student_id": user.user_id, "type": "student_rating"},
                {"_id": 0}
            )
            if rated:
                completed.append(cls)
            else:
                pending_rating.append(cls)
        elif cls_date > today_str and status in ('scheduled',):
            upcoming.append(cls)
        elif cls_end_date < today_str and status not in ('completed', 'cancelled'):
            # End-of-day auto-progression: if teacher never started, mark as no-show
            # so the demo allowance can be refunded; otherwise treat as completed.
            if not cls.get("started_at_actual"):
                await db.class_sessions.update_one(
                    {"class_id": cls["class_id"]},
                    {"$set": {"status": "teacher_no_show", "teacher_no_show": True}}
                )
                cls["status"] = "teacher_no_show"
                cls["teacher_no_show"] = True
                cancelled.append(cls)
            else:
                await db.class_sessions.update_one(
                    {"class_id": cls["class_id"]}, {"$set": {"status": "completed"}}
                )
                cls["status"] = "completed"
                pending_rating.append(cls)
        else:
            completed.append(cls)

    # Get student assignments with payment status
    assignments = await db.student_teacher_assignments.find(
        {"student_id": user.user_id, "status": "approved"}, {"_id": 0}
    ).to_list(100)

    return {
        "credits": user.credits,
        "live_classes": live_classes,
        "upcoming_classes": upcoming,
        "completed_classes": completed,
        "pending_rating": pending_rating,
        "cancelled_classes": cancelled,
        "past_classes": completed + pending_rating,
        "assignments": assignments
    }


@router.get("/student/my-transactions")
async def student_transactions(request: Request, authorization: Optional[str] = Header(None)):
    """Get student's credit transaction history"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    transactions = await db.transactions.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return transactions


@router.post("/student/rate-class")
async def student_rate_class(data: StudentFeedbackRating, request: Request, authorization: Optional[str] = Header(None)):
    """Student rates a completed class - impacts teacher rating"""
    import uuid
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    cls = await db.class_sessions.find_one({"class_id": data.class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Can only rate completed classes")

    # Check if already rated
    existing = await db.feedback.find_one(
        {"class_id": data.class_id, "student_id": user.user_id, "type": "student_rating"}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already rated this class")

    feedback_doc = {
        "feedback_id": f"fb_{uuid.uuid4().hex[:12]}",
        "class_id": data.class_id,
        "student_id": user.user_id,
        "student_name": user.name,
        "teacher_id": cls["teacher_id"],
        "type": "student_rating",
        "rating": data.rating,
        "comments": data.comments,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.feedback.insert_one(feedback_doc)

    # If bad rating (<=2), record as bad_feedback event
    if data.rating <= 2:
        await record_rating_event(cls["teacher_id"], "bad_feedback", f"Rating {data.rating}/5 from {user.name}: {data.comments[:100]}")
    else:
        await recalc_teacher_rating(cls["teacher_id"])

    return {"message": "Rating submitted. Thank you!"}


@router.post("/student/update-profile")
async def update_student_profile(profile: StudentProfileUpdate, request: Request, authorization: Optional[str] = Header(None)):
    """Student updates limited profile details (contact info only, no class/course changes)"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    # Students can only update contact info, NOT academic fields (grade, institute, goal)
    update_fields = {}
    if profile.phone is not None:
        # Phone uniqueness check
        if profile.phone.strip():
            phone_exists = await db.users.find_one({"phone": profile.phone.strip(), "user_id": {"$ne": user.user_id}}, {"_id": 0, "email": 1})
            if phone_exists:
                raise HTTPException(status_code=400, detail="Phone number already registered with another account")
        update_fields['phone'] = profile.phone
    if profile.state is not None:
        update_fields['state'] = profile.state
    if profile.city is not None:
        update_fields['city'] = profile.city
    if profile.country is not None:
        update_fields['country'] = profile.country
    if profile.preferred_time_slot is not None:
        update_fields['preferred_time_slot'] = profile.preferred_time_slot

    if update_fields:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update_fields})

    return {"message": "Profile updated successfully"}


@router.get("/student/nag-check")
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


@router.get("/student/enrollment-status")
async def student_enrollment_status(request: Request, authorization: Optional[str] = Header(None)):
    """Check if student is enrolled in a paid course"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")

    approved = await db.student_teacher_assignments.find_one(
        {"student_id": user.user_id, "status": "approved"}, {"_id": 0}
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    active_classes = await db.class_sessions.find(
        {"assigned_student_id": user.user_id, "is_demo": False,
         "status": {"$in": ["scheduled", "in_progress"]},
         "end_date": {"$gte": today}},
        {"_id": 0}
    ).to_list(100)

    demo_classes = await db.class_sessions.find(
        {"assigned_student_id": user.user_id, "is_demo": True},
        {"_id": 0}
    ).to_list(10)
    demo_completed = len(demo_classes) > 0

    is_enrolled = bool(approved)

    # Check if student was previously finished (all classes done, marked by counsellor)
    finished = await db.student_teacher_assignments.find_one(
        {"student_id": user.user_id, "status": "finished"},
        {"_id": 0, "assignment_id": 1}
    )
    is_finished = bool(finished) and not is_enrolled

    return {
        "is_enrolled": is_enrolled,
        "is_finished": is_finished,
        "has_approved_teacher": bool(approved),
        "active_class_count": len(active_classes),
        "demo_completed": demo_completed,
        "teacher_name": approved.get("teacher_name") if approved else None
    }


@router.get("/student/demo-feedback-received")
async def student_demo_feedback_received(request: Request, authorization: Optional[str] = Header(None)):
    """Student views feedback received from teachers on their demo sessions"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")

    feedbacks = await db.demo_feedback.find(
        {"student_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    for fb in feedbacks:
        if fb.get("teacher_id"):
            teacher = await db.users.find_one({"user_id": fb["teacher_id"]}, {"_id": 0, "name": 1, "teacher_code": 1})
            fb["teacher_name"] = teacher.get("name") if teacher else "Unknown"
            fb["teacher_code"] = teacher.get("teacher_code") if teacher else ""

    return feedbacks
