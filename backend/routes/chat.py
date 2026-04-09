"""Chat routes"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import ChatMessage
from services.auth import get_current_user

router = APIRouter()


@router.post("/chat/send")
async def send_chat_message(data: ChatMessage, request: Request, authorization: Optional[str] = Header(None)):
    """Send a scoped chat message"""
    user = await get_current_user(request, authorization)

    recipient = await db.users.find_one({"user_id": data.recipient_id}, {"_id": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # PERMISSION CHECK
    if user.role == "teacher":
        assigned = await db.student_teacher_assignments.find_one(
            {"teacher_id": user.user_id, "student_id": data.recipient_id, "status": {"$in": ["pending", "approved"]}},
            {"_id": 0}
        )
        if not assigned and recipient.get("role") != "admin":
            raise HTTPException(status_code=403, detail="You can only message your assigned students")
    elif user.role == "student":
        assigned_teacher = await db.student_teacher_assignments.find_one(
            {"student_id": user.user_id, "teacher_id": data.recipient_id, "status": {"$in": ["pending", "approved"]}},
            {"_id": 0}
        )
        is_counsellor = recipient.get("role") == "counsellor"
        if not assigned_teacher and not is_counsellor:
            raise HTTPException(status_code=403, detail="You can only message your assigned teacher or a counsellor")
    # Admin and Counsellor: global access - no restriction

    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    msg_doc = {
        "message_id": msg_id,
        "sender_id": user.user_id,
        "sender_name": user.name,
        "sender_role": user.role,
        "sender_code": getattr(user, 'teacher_code', None) or getattr(user, 'student_code', None) or user.user_id,
        "recipient_id": data.recipient_id,
        "recipient_name": recipient.get("name"),
        "recipient_role": recipient.get("role"),
        "recipient_code": recipient.get("teacher_code") or recipient.get("student_code") or data.recipient_id,
        "message": data.message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chat_messages.insert_one(msg_doc)

    return {"message": "Message sent", "message_id": msg_id}


@router.get("/chat/conversations")
async def get_conversations(request: Request, authorization: Optional[str] = Header(None)):
    """Get all conversations for the current user"""
    user = await get_current_user(request, authorization)

    messages = await db.chat_messages.find(
        {"$or": [{"sender_id": user.user_id}, {"recipient_id": user.user_id}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(5000)

    convos = {}
    for msg in messages:
        partner_id = msg["recipient_id"] if msg["sender_id"] == user.user_id else msg["sender_id"]
        if partner_id not in convos:
            convos[partner_id] = {
                "partner_id": partner_id,
                "partner_name": msg["recipient_name"] if msg["sender_id"] == user.user_id else msg["sender_name"],
                "partner_role": msg["recipient_role"] if msg["sender_id"] == user.user_id else msg["sender_role"],
                "partner_code": msg.get("recipient_code") if msg["sender_id"] == user.user_id else msg.get("sender_code"),
                "last_message": msg["message"],
                "last_message_at": msg["created_at"],
                "unread_count": 0
            }
        if msg["recipient_id"] == user.user_id and not msg.get("read"):
            convos[partner_id]["unread_count"] += 1

    return list(convos.values())


@router.get("/chat/messages/{partner_id}")
async def get_chat_messages(partner_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get messages between current user and partner"""
    user = await get_current_user(request, authorization)

    messages = await db.chat_messages.find(
        {"$or": [
            {"sender_id": user.user_id, "recipient_id": partner_id},
            {"sender_id": partner_id, "recipient_id": user.user_id}
        ]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    # Mark as read
    await db.chat_messages.update_many(
        {"sender_id": partner_id, "recipient_id": user.user_id, "read": False},
        {"$set": {"read": True}}
    )

    return messages


@router.get("/chat/contacts")
async def get_chat_contacts(request: Request, authorization: Optional[str] = Header(None)):
    """Get contacts the user is allowed to message"""
    user = await get_current_user(request, authorization)
    contacts = []

    if user.role == "admin" or user.role == "counsellor":
        users = await db.users.find(
            {"user_id": {"$ne": user.user_id}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "teacher_code": 1, "student_code": 1}
        ).to_list(5000)
        contacts = users
    elif user.role == "teacher":
        assignments = await db.student_teacher_assignments.find(
            {"teacher_id": user.user_id, "status": {"$in": ["pending", "approved"]}},
            {"_id": 0, "student_id": 1}
        ).to_list(100)
        student_ids = [a["student_id"] for a in assignments]
        if student_ids:
            contacts = await db.users.find(
                {"user_id": {"$in": student_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "student_code": 1}
            ).to_list(100)
    elif user.role == "student":
        assignments = await db.student_teacher_assignments.find(
            {"student_id": user.user_id, "status": {"$in": ["pending", "approved"]}},
            {"_id": 0, "teacher_id": 1}
        ).to_list(10)
        teacher_ids = [a["teacher_id"] for a in assignments]
        if teacher_ids:
            teachers = await db.users.find(
                {"user_id": {"$in": teacher_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "teacher_code": 1}
            ).to_list(10)
            contacts.extend(teachers)
        counsellors = await db.users.find(
            {"role": "counsellor"},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(100)
        contacts.extend(counsellors)

    return contacts
