"""Background tasks for cleanup and pre-class alerts"""
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta

from database import db
from services.helpers import send_email

logger = logging.getLogger(__name__)


async def background_cleanup_task():
    """Check every hour: Students with no enrollment/demo for 24h get warned, then deleted after another 24h"""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            one_day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            students = await db.users.find(
                {"role": "student"}, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "created_at": 1}
            ).to_list(5000)

            for s in students:
                sid = s["user_id"]
                # Check for any active assignment
                has_assignment = await db.student_teacher_assignments.find_one(
                    {"student_id": sid, "status": {"$in": ["pending", "approved"]}}, {"_id": 0}
                )
                if has_assignment:
                    continue

                # Check for any scheduled classes or demos
                has_class = await db.class_sessions.find_one(
                    {"assigned_student_id": sid, "status": {"$in": ["scheduled", "in_progress"]}}, {"_id": 0}
                )
                if has_class:
                    continue

                # Check for any demo requests
                has_demo = await db.demo_requests.find_one(
                    {"student_id": sid, "status": {"$in": ["pending", "accepted"]}}, {"_id": 0}
                )
                if has_demo:
                    continue

                # Check if created > 24 hours ago
                created = s.get("created_at", "")
                if created and created < one_day_ago:
                    # Check if already warned
                    warned = await db.notifications.find_one(
                        {"user_id": sid, "type": "inactivity_warning"}, {"_id": 0}
                    )
                    if not warned:
                        # Send 24-hour warning notification
                        await db.notifications.insert_one({
                            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                            "user_id": sid,
                            "type": "inactivity_warning",
                            "title": "Account Inactivity Warning",
                            "message": "Your account has been inactive for 24 hours with no demo or class assigned. Please book a demo to keep your account active. Your account will be deleted in 24 hours if no action is taken.",
                            "read": False,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        })
                        await send_email(s.get("email", ""), "Kaimera Learning - Account Inactivity Warning",
                            f"<p>Hi {s.get('name', '')}, your Kaimera Learning account has been inactive for 24 hours with no demo or class assigned. Please book a demo to keep your account active. <b>Your account will be permanently deleted in 24 hours if no action is taken.</b></p>")
                        logger.info(f"Sent 24h inactivity warning to {s.get('name', '')} ({s.get('email', '')})")
                    else:
                        # Already warned — delete if 24+ hours since warning
                        warn_date = warned.get("created_at", "")
                        if warn_date and warn_date < (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat():
                            await db.users.delete_one({"user_id": sid})
                            await db.user_sessions.delete_many({"user_id": sid})
                            logger.info(f"Auto-deleted inactive student (48h total): {s.get('name', '')} ({s.get('email', '')})")
        except Exception as e:
            logger.error(f"Background cleanup error: {e}")


async def background_preclass_alert_task():
    """Check every 10 min: Send notification 30 min before class"""
    while True:
        try:
            await asyncio.sleep(600)  # Check every 10 minutes
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            alert_time = (now + timedelta(minutes=30)).strftime("%H:%M")
            current_time = now.strftime("%H:%M")

            # Find classes today starting in ~30 minutes
            classes_today = await db.class_sessions.find(
                {"date": {"$lte": today}, "end_date": {"$gte": today},
                 "status": {"$in": ["scheduled", "in_progress"]},
                 "start_time": {"$lte": alert_time, "$gt": current_time}},
                {"_id": 0}
            ).to_list(100)

            for cls in classes_today:
                alert_key = f"preclass_alert_{cls['class_id']}_{today}"
                already_sent = await db.notifications.find_one(
                    {"notification_id": alert_key}, {"_id": 0}
                )
                if already_sent:
                    continue

                for s in cls.get("enrolled_students", []):
                    await db.notifications.insert_one({
                        "notification_id": alert_key,
                        "user_id": s["user_id"],
                        "type": "preclass_alert",
                        "title": "Class Starting Soon!",
                        "message": f"Your class '{cls['title']}' starts at {cls['start_time']} today. Get ready!",
                        "read": False,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    # Send email
                    student = await db.users.find_one({"user_id": s["user_id"]}, {"_id": 0, "email": 1, "name": 1})
                    if student:
                        await send_email(student.get("email", ""), "Kaimera - Class Starting Soon!",
                            f"<p>Hi {student.get('name', '')}, your class <b>{cls['title']}</b> starts at <b>{cls['start_time']}</b> today!</p>")

                logger.info(f"Sent pre-class alerts for {cls['title']}")
        except Exception as e:
            logger.error(f"Pre-class alert error: {e}")
