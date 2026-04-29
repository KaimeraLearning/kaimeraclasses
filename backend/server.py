import os
import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from database import db, client
from services.auth import seed_admin, seed_system_pricing
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

app = FastAPI(
    docs_url="/docs" if os.environ.get("ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.environ.get("ENABLE_DOCS", "false").lower() == "true" else None,
    openapi_url="/openapi.json" if os.environ.get("ENABLE_DOCS", "false").lower() == "true" else None,
)


@app.exception_handler(ConnectionFailure)
@app.exception_handler(ServerSelectionTimeoutError)
async def db_error_handler(request: Request, exc: Exception):
    logger.error(f"Database connection error: {exc}")
    return JSONResponse(status_code=503, content={"detail": "Database connection error. Please try again later."})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "; ".join([f"{e.get('loc', [''])[- 1]}: {e.get('msg', '')}" for e in errors])
    return JSONResponse(status_code=422, content={"detail": f"Invalid input: {msg}"})


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    # Don't catch HTTP exceptions — let FastAPI handle them normally with proper detail messages
    if isinstance(exc, StarletteHTTPException):
        raise exc
    logger.error(f"Unhandled error on {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": f"Server error: {type(exc).__name__}. Please try again."})

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- API Key gate -----
# Every request to /api/* must carry the x-api-key header matching API_KEY env.
# Exempts: CORS preflight (OPTIONS) and external webhooks that we cannot control.
_API_KEY = os.environ.get("API_KEY", "").strip()
_API_KEY_EXEMPT_PATHS = {
    "/api/webhook/razorpay",
}
# Allowed Origin/Referer domains — request must come from one of these (browser-set headers).
# Pulled from CORS_ORIGINS so config stays in one place. "*" disables the check.
_ALLOWED_ORIGINS_RAW = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
_ENFORCE_ORIGIN = "*" not in _ALLOWED_ORIGINS_RAW and len(_ALLOWED_ORIGINS_RAW) > 0


def _origin_allowed(request: Request) -> bool:
    if not _ENFORCE_ORIGIN:
        return True
    origin = request.headers.get("origin") or ""
    referer = request.headers.get("referer") or ""
    for allowed in _ALLOWED_ORIGINS_RAW:
        if origin == allowed or referer.startswith(allowed):
            return True
    return False


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    path = request.url.path or ""

    # Always allow CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    # External webhooks we cannot control (Razorpay) bypass everything
    if path in _API_KEY_EXEMPT_PATHS:
        return await call_next(request)

    # Any non-/api/* path (e.g. /docs, /redoc, /openapi.json, /, /favicon.ico) is FORBIDDEN.
    # This makes the entire API surface invisible to public scanners.
    if not path.startswith("/api/"):
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden."},
        )

    # /api/* — require x-api-key header
    if _API_KEY:
        provided = request.headers.get("x-api-key") or request.headers.get("X-API-Key") or ""
        if provided != _API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )

    # /api/* — require Origin/Referer to match allow-list (when CORS_ORIGINS is not "*")
    if not _origin_allowed(request):
        return JSONResponse(
            status_code=403,
            content={"detail": "Request origin not allowed."},
        )

    return await call_next(request)

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
    await seed_system_pricing()
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
