# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counselor, Teacher, Student.
Flow: Counselor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts
- Backend: FastAPI (Python), Modular architecture (routes/, models/, services/, tasks/)
- Database: MongoDB (Motor async driver)
- Auth: Session-based (single device) + Emergent Google OAuth + Email OTP
- Payments: Stripe (webhook handling)
- Video: Jitsi Meet (CDN)
- Email: Resend API

## Architecture

### Backend Structure
```
/app/backend/
  server.py              # Thin orchestrator
  database.py            # MongoDB connection
  models/schemas.py      # Pydantic models
  services/auth.py       # Auth + single device session + blocked user check
  services/helpers.py    # Code generators, email, OTP
  services/rating.py     # Teacher rating system
  tasks/background.py    # Cleanup + pre-class alerts
  routes/               # 10 modules, 125+ endpoints
```

### Security
- Single device session enforcement
- Blocked user enforcement (403 + session purge)
- Email/phone uniqueness (DB index + app-level across all roles)
- Credit floor, atomic payments, class delete refunds
- Proof integrity (one per class/day)
- OTP brute force protection
- Bank details locked after first entry (teacher/counselor)

### Profile System (Teacher & Counselor)
- Profile picture upload, Bio, Age, DOB, Address, Education, Interests, Experience
- KLAT Score (Teacher) / KL-CAT Score (Counselor)
- Bank Details (locked after first entry, admin-only override)
- PDF Resume upload (viewable by admin/counselor/students)
- Counselor ID (KLC-XXXXXX format)
- Bank details visible to admin only

### Chat System
- Demo-aware contacts (teacher accepts demo -> mutual chat enabled)
- Permission-scoped messaging

## Completed Work
- [Apr 10, 2026] **Major Feature Batch**: Spelling fix (Counselor), teacher/counselor profile system (KLAT/KL-CAT, bank lock, resume, profile pic), proof screenshot upload, removed preferred time from admin create-student, global error handling fix (no more "JSON response error"). All verified 100% (23/23 backend + all frontend).
- [Apr 10, 2026] Single device session, demo-based chat, student locked view with demo classes + Chat button
- [Apr 10, 2026] Security hardening (12 fixes) + Backend modular refactor (5220→90 line server.py)
- Full EdTech CRM: 4-role dashboards, Operations Center, wallet, demo booking, chat, complaints, teacher rating/suspension, learning kits.

## Remaining Backlog
- P1: Verify Jitsi screenshot fix in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
