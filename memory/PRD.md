# Kaimera Learning - Product Requirements Document

## Original Problem Statement
EdTech CRM/Management Platform with roles: Admin, Counselor, Teacher, Student. Features wallet-based credits, Stripe integration, Counselor dashboard, Teacher schedule management, class proofs with screenshots, complaint system, Video integration (Jitsi), Demo Booking & Tracking workflow, Email Notifications, Global Financial Controls, Conditional Student UI Lockdown.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Backend**: FastAPI (modular routes)
- **Database**: MongoDB
- **Video**: Jitsi Meet API
- **Auth**: Cookie-based sessions + Google Auth (Emergent)
- **Payments**: Stripe
- **Email**: Resend

## Code Structure
```
/app/backend/
  server.py, database.py
  models/schemas.py
  services/auth.py, helpers.py, rating.py
  tasks/background.py
  routes/admin.py, auth.py, chat.py, classes.py, counsellor.py, demo.py, general.py, payments.py, student.py, teacher.py
/app/frontend/src/
  components/ (ViewProfilePopup.js, ui/)
  pages/ (*Dashboard.js, *Profile.js)
  utils/api.js
```

## Spelling Convention
- Internal: `counsellor` (DB, API paths, filenames)
- User-facing: `Counselor`

## Completed Features
- Full role-based dashboard (Admin, Teacher, Student, Counselor)
- Wallet-based credit system + Stripe integration
- Demo-first enrollment workflow
- Jitsi video class integration
- Teacher rating & penalty/suspension system
- Permission-based scoped chat
- Single-device session enforcement
- KLAT/KL-CAT scoring + PDF resume upload
- Class proofs with screenshot upload
- Complaint system
- Notification system
- Email OTP (Resend)
- Global dynamic financial controls (Admin)
- Modular backend architecture (routes/, models/, services/, tasks/)
- **ViewProfilePopup** - unified profile popup across all dashboards (Feb 2026)
- **Auto-refresh on tab focus** - all 3 dashboards refresh data on visibilitychange (Feb 2026)
- **One-time proof/feedback UI lockdown** - frontend properly guards duplicate submissions (Feb 2026)

## Backlog
### P2
- Verify Resend domain for production email

### P3
- Real-time WebSocket notifications/chat
- Student progress PDF reports
