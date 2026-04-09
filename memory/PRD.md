# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Flow: Counsellor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth + Email OTP verification
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)
- Email: Resend API (transactional + OTP emails)

## Architecture (Updated Apr 9, 2026)

### Admin Dashboard = "Operations Center"
Three main sections with sub-tabs:
1. **User Management**: Identity Creator, Staff & Student Directory, Credentials & Access
2. **Financials**: Transaction Ledger, Proofs & Approvals, **System Pricing** (4 global rates + Purge System)
3. **Reports**: Counsellor Tracking, Class Overview, Complaints

### System Pricing (Unified Rates Dashboard)
- 4 global rate fields: Demo Class Rate (student), Regular Class Fee (student), Demo Session Credit (teacher), Regular Class Pay (teacher)
- All financial transactions pull from `system_pricing` collection — no hardcoded values
- **System Purge**: One-click clean slate — deletes all non-admin data, resets counters to zero

### Admin Student Profile Override
- Edit Profile button in User Drawer (students only)
- All fields editable: name, email, phone, credits, grade, institute, goal, preferred_time_slot, state, city, country, bio

### Counsellor Dashboard (Refactored Apr 9, 2026)
- **Tabbed layout**: Available / Active / Rejected / Reassignment / Renewals
- **Pagination**: 10 items per page with page controls
- Student cards show: Demo Teacher Name + Demo Feedback from teacher
- Assignment modal: Teacher selection, Class Frequency, Specific Days, Demo Performance Notes
- Active assignments show frequency/days/notes metadata

### Teacher Dashboard
- **Cancel disables Join Live**: When student cancels, Start/Rejoin buttons hide, showing "Session cancelled by student"
- **Reschedule**: Button appears only for current cancelled session
- **Mandatory Demo Feedback**: Violet alert banner shows pending demos requiring feedback
- Demo Feedback Dialog: Performance rating, Recommended frequency, Feedback notes — auto-notifies counsellors
- **Schedule Planner** (replaces Content Planner): Calendar view of booked classes with day-detail panel

### Student Dashboard
- **Locked profile**: Grade, Institute, Goal are READ-ONLY (only Admin can edit)
- Students can only update: Phone, State, City, Country, Preferred Time
- **Book Demo hidden** after demo is conducted
- UI Lockdown Mode for unenrolled students

### Security & Auto-Deletion
- **24h/48h Auto-Delete**: Students with no demo/class after 24h get warning notification + email. After another 24h (48h total), auto-deleted
- **Pre-class alerts**: 30 min before booked session, notification + email sent

## Implemented Features (All DONE)

### System Overhaul (DONE - Apr 9, 2026)
- Phase 1: System Purge endpoint + Admin UI button
- Phase 2: Dynamic pricing — all transactions read from system_pricing
- Phase 3: Counsellor tabbed dashboard with pagination, demo teacher visibility
- Phase 3: Teacher Schedule Planner (replaced Content Planner)
- Phase 4: Student profile locked, Book Demo hidden after demo, 24h/48h auto-delete
- Phase 5: Cancel disables Join Live, mandatory teacher demo feedback

### Previous (All DONE)
- Operations & Logic Refactor: Assignment fields, reschedule UI, admin pricing, student edit
- Operations Center Refactoring: Identity Creator, unified list, drill-down drawer
- OTP Email Verification, Login Page Redesign
- Teacher Dashboard overhaul, Wallet colors, Badge templates
- Global search, credential management, counsellor tracking
- Demo Booking, Video (Jitsi), Learning Kit, Email Notifications
- Proof Pipeline, Complaints, Notifications, Stripe webhooks

## Key API Endpoints
- Auth: /api/auth/register, login, send-otp, verify-otp, session, me, logout
- Admin: /api/admin/create-user, block-user, delete-user, reset-password, purge-system
- Admin: /api/admin/set-pricing, get-pricing, edit-student/{user_id}
- Counsellor: /api/counsellor/dashboard (includes demo_teacher_name), student-profile/{id}
- Teacher: /api/teacher/submit-demo-feedback, pending-demo-feedback, schedule, reschedule-class
- Student: /api/student/update-profile (locked: only contact fields)

## Remaining Backlog
- P2: Jitsi screenshot fix (captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Modular refactor of server.py into route files
- P3: Real-time WebSocket notifications
- P3: Student progress PDF reports
