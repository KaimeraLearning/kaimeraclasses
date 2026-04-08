# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Build a complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student. 
Flow: Students sign up (0 credits) -> Counsellor assigns student to Teacher -> Teacher approves -> Teacher creates classes for student (auto-enrolling, credits deducted). Admin/Counsellor sets pricing. Teachers submit class proofs for counsellor verification to earn wallet credits.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key)

## Core Workflow
1. Student registers (0 credits) → Admin adds credits
2. Counsellor assigns student to teacher with custom price
3. Teacher approves assignment (24hr window)
4. Teacher creates class for that student → auto-enrollment + credit deduction
5. Teacher submits proof after class → Counsellor verifies → Teacher earns wallet credits
6. If class duration expires: rebook within 3 days OR release to counsellor pool

## Implemented Features (as of Feb 2026)

### Phase 1 - Core CRM (DONE)
- 4-role system: Admin, Counsellor, Teacher, Student
- Session-based auth + Google OAuth
- Admin: create teachers/counsellors, set pricing, approve teachers, adjust credits
- Counsellor: assign students to teachers, view all students/teachers
- Teacher: approve students, create classes (1:1 or group), manage schedule
- Student: browse assigned classes, auto-enrollment, cancel bookings
- Stripe payment integration (test key)

### Phase 2 - Profile & Verification (DONE)
- Student profile popup in Counsellor Dashboard (institute, goal, preferred time slot, credits, assignment info, class history)
- Student profile edit (phone, institute, goal, preferred time slot)
- Teacher/Student profile popups with full details
- Separate scalable pages: CounsellorStudents, TeacherClasses, TeacherSchedule

### Phase 3 - Demo & Proofs (DONE)
- Demo session flow: is_demo toggle on class creation, uses demo pricing from system settings
- Teacher class verification: submit proof (feedback, performance rating, topics covered, screenshot)
- Counsellor proof verification page: approve/reject proofs, reviewer notes
- Teacher wallet credits on proof approval (uses system pricing earning rates)

### Phase 4 - Complaints & Reassignment (DONE)
- Complaint system: students, teachers, counsellors can raise complaints
- Admin complaint management: view all complaints, resolve/close
- Shared complaints page accessible from all dashboards
- Auto-reassignment logic: expired classes flagged, rebook within 3 days or release student

## API Endpoints
### Auth: /api/auth/register, /api/auth/login, /api/auth/session, /api/auth/me, /api/auth/logout
### Student: /api/student/dashboard, /api/student/update-profile, /api/classes/browse, /api/classes/book, /api/classes/cancel/{id}
### Teacher: /api/teacher/dashboard, /api/teacher/approve-assignment, /api/teacher/submit-proof, /api/teacher/my-proofs, /api/teacher/update-profile, /api/classes/create, /api/classes/delete/{id}
### Counsellor: /api/counsellor/dashboard, /api/counsellor/student-profile/{id}, /api/counsellor/pending-proofs, /api/counsellor/all-proofs, /api/counsellor/verify-proof, /api/counsellor/expired-classes, /api/counsellor/reassign-student
### Admin: /api/admin/teachers, /api/admin/students, /api/admin/classes, /api/admin/transactions, /api/admin/complaints, /api/admin/resolve-complaint, /api/admin/assign-student, /api/admin/create-teacher, /api/admin/create-counsellor, /api/admin/set-pricing, /api/admin/get-pricing, /api/admin/adjust-credits, /api/admin/approve-teacher, /api/admin/all-assignments, /api/admin/emergency-assignments
### Complaints: /api/complaints/create, /api/complaints/my

## Remaining Backlog
- P2: Stripe integration robustness (webhook handling, real payment flow)
- P3: Video integration for live classes
- P3: Refactor server.py into modular routers (auth, admin, teacher, student, counsellor)

## Architecture
```
/app/backend/server.py - All API endpoints (FastAPI)
/app/frontend/src/
  App.js - Route definitions
  pages/ - StudentDashboard, TeacherDashboard, AdminDashboard, CounsellorDashboard,
           CounsellorStudents, CounsellorProofs, TeacherClasses, TeacherSchedule,
           ComplaintsPage, BrowseClasses, VideoClass, PaymentSuccess, Login, AuthCallback
  components/ui/ - Shadcn components
  components/ProtectedRoute.js - Role-based route guard
```
