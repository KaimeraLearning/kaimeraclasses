import os
import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

from database import db, client
from services.auth import seed_admin
from services.helpers import generate_teacher_code, generate_student_code
from tasks.background import background_cleanup_task, background_preclass_alert_task

from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.teacher import router as teacher_router
from routes.student import router as student_router
from routes.classes import router as classes_router
from routes.chat import router as chat_router
from routes.counsellor import router as counsellor_router
from routes.demo import router as demo_router
from routes.payments import router as payments_router
from routes.general import router as general_router
from routes.attendance import router as attendance_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(teacher_router, prefix="/api")
app.include_router(student_router, prefix="/api")
app.include_router(classes_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(counsellor_router, prefix="/api")
app.include_router(demo_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(general_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    await seed_admin()
    # Create unique indexes for security
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    # Backfill teacher_code for existing teachers without one
    teachers_without_code = await db.users.find(
        {"role": "teacher", "$or": [{"teacher_code": None}, {"teacher_code": {"$exists": False}}]},
        {"_id": 0}
    ).to_list(1000)
    for t in teachers_without_code:
        code = await generate_teacher_code()
        await db.users.update_one({"user_id": t["user_id"]}, {"$set": {"teacher_code": code}})
        logger.info(f"Backfilled teacher_code {code} for {t['name']}")
    # Backfill student_code for existing students without one
    students_without_code = await db.users.find(
        {"role": "student", "$or": [{"student_code": None}, {"student_code": {"$exists": False}}]},
        {"_id": 0}
    ).to_list(5000)
    for s in students_without_code:
        code = await generate_student_code()
        await db.users.update_one({"user_id": s["user_id"]}, {"$set": {"student_code": code}})
        logger.info(f"Backfilled student_code {code} for {s.get('name', s['email'])}")
    logger.info("Kaimera Learning API started")
    # Start background tasks
    asyncio.create_task(background_cleanup_task())
    asyncio.create_task(background_preclass_alert_task())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
