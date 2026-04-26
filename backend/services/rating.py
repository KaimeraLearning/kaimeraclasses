"""Teacher rating calculation and event recording"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

from database import db

logger = logging.getLogger(__name__)


async def recalc_teacher_rating(teacher_id: str):
    """Recalculate a teacher's star rating based on student feedback and cancellations"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Get admin-configured rating deduction per cancellation
    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    cancel_deduction = pricing.get("cancel_rating_deduction", 0.2) if pricing else 0.2

    # Get all student feedback ratings for this teacher
    feedbacks = await db.feedback.find(
        {"teacher_id": teacher_id, "rating": {"$exists": True}},
        {"_id": 0, "rating": 1}
    ).to_list(5000)
    avg_feedback = sum(f["rating"] for f in feedbacks) / len(feedbacks) if feedbacks else 5.0

    # Count monthly cancellations by teacher
    monthly_cancellations = await db.teacher_rating_events.count_documents({
        "teacher_id": teacher_id, "event": "cancellation",
        "created_at": {"$gte": month_start}
    })

    # Count bad feedbacks (rating <= 2)
    bad_feedbacks = sum(1 for f in feedbacks if f["rating"] <= 2)

    # Rating: start at avg_feedback, subtract configurable amount per cancellation, 0.3 per bad feedback
    penalty = (monthly_cancellations * cancel_deduction) + (bad_feedbacks * 0.3)
    star_rating = round(max(0, min(5, avg_feedback - penalty)), 1)

    # Auto-suspension: 5+ cancellations this month
    is_suspended = False
    suspension_until = None
    if monthly_cancellations >= 5:
        existing_suspension = await db.users.find_one(
            {"user_id": teacher_id, "suspended_until": {"$exists": True}}, {"_id": 0, "suspended_until": 1}
        )
        if existing_suspension and existing_suspension.get("suspended_until"):
            susp_until = existing_suspension["suspended_until"]
            if isinstance(susp_until, str):
                susp_until = datetime.fromisoformat(susp_until)
            if susp_until.tzinfo is None:
                susp_until = susp_until.replace(tzinfo=timezone.utc)
            if now < susp_until:
                is_suspended = True
                suspension_until = susp_until.isoformat()
        else:
            # New suspension: 3 days
            suspension_until = (now + timedelta(days=3)).isoformat()
            is_suspended = True

    update = {
        "star_rating": star_rating,
        "monthly_cancellations": monthly_cancellations,
        "is_suspended": is_suspended,
        "rating_details": {
            "avg_feedback": round(avg_feedback, 2),
            "total_feedbacks": len(feedbacks),
            "bad_feedbacks": bad_feedbacks,
            "monthly_cancellations": monthly_cancellations,
            "penalty": round(penalty, 2)
        }
    }
    if suspension_until:
        update["suspended_until"] = suspension_until
    await db.users.update_one({"user_id": teacher_id}, {"$set": update})
    return star_rating, is_suspended


async def record_rating_event(teacher_id: str, event: str, details: str = ""):
    """Record a rating event (cancellation, bad_feedback) and recalculate"""
    await db.teacher_rating_events.insert_one({
        "event_id": f"rev_{uuid.uuid4().hex[:12]}",
        "teacher_id": teacher_id,
        "event": event,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return await recalc_teacher_rating(teacher_id)
