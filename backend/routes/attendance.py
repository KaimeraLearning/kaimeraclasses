"""Attendance routes"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from services.auth import get_current_user

router = APIRouter()


@router.post("/attendance/mark")
async def mark_attendance(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher marks daily attendance for a student"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    body = await request.json()
    student_id = body.get("student_id")
    date = body.get("date")  # YYYY-MM-DD
    status = body.get("status", "present")  # present, absent, late

    if not student_id or not date:
        raise HTTPException(status_code=400, detail="student_id and date required")

    if status not in ["present", "absent", "late"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use: present, absent, late")

    # Verify the student is assigned to this teacher (paid)
    assignment = await db.student_teacher_assignments.find_one(
        {"teacher_id": user.user_id, "student_id": student_id, "status": "approved", "payment_status": "paid"},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Student not found in your class")

    # Upsert attendance record
    attendance_id = f"att_{uuid.uuid4().hex[:12]}"
    await db.attendance.update_one(
        {"teacher_id": user.user_id, "student_id": student_id, "date": date},
        {"$set": {
            "attendance_id": attendance_id,
            "teacher_id": user.user_id,
            "teacher_name": user.name,
            "student_id": student_id,
            "student_name": assignment.get("student_name"),
            "date": date,
            "status": status,
            "marked_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )

    return {"message": f"Attendance marked as {status} for {date}"}


@router.get("/attendance/teacher")
async def teacher_attendance_history(request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance records for a teacher's students"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    params = dict(request.query_params)
    query = {"teacher_id": user.user_id}

    if params.get("student_id"):
        query["student_id"] = params["student_id"]
    if params.get("date_from"):
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = params["date_from"]
    if params.get("date_to"):
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = params["date_to"]

    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@router.get("/attendance/student")
async def student_attendance_history(request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance records for a student"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    params = dict(request.query_params)
    query = {"student_id": user.user_id}

    if params.get("date_from"):
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = params["date_from"]
    if params.get("date_to"):
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = params["date_to"]

    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@router.get("/attendance/summary/{student_id}")
async def attendance_summary(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance summary for a student"""
    user = await get_current_user(request, authorization)
    if user.role not in ["teacher", "admin", "counsellor"] and user.user_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    records = await db.attendance.find({"student_id": student_id}, {"_id": 0}).to_list(1000)

    total = len(records)
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")
    late = sum(1 for r in records if r.get("status") == "late")
    percentage = round((present / total) * 100, 1) if total > 0 else 0

    return {
        "student_id": student_id,
        "total_days": total,
        "present": present,
        "absent": absent,
        "late": late,
        "attendance_percentage": percentage
    }
