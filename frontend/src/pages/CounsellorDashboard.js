import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Users, BookOpen, UserPlus, ShieldCheck, MessageSquare, Clock, User, MapPin, Target, CalendarClock, Zap } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CounsellorDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [unassignedStudents, setUnassignedStudents] = useState([]);
  const [allStudents, setAllStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [activeAssignments, setActiveAssignments] = useState([]);
  const [rejectedAssignments, setRejectedAssignments] = useState([]);
  const [pendingProofsCount, setPendingProofsCount] = useState(0);
  const [expiredClasses, setExpiredClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [showTeacherDialog, setShowTeacherDialog] = useState(false);
  const [showStudentDialog, setShowStudentDialog] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProfile, setStudentProfile] = useState(null);
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [selectedTeacherForAssign, setSelectedTeacherForAssign] = useState('');
  const [customPrice, setCustomPrice] = useState('100');

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes, proofsRes, expiredRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/counsellor/dashboard`, { credentials: 'include' }),
        fetch(`${API}/counsellor/pending-proofs`, { credentials: 'include' }),
        fetch(`${API}/counsellor/expired-classes`, { credentials: 'include' })
      ]);

      if (!userRes.ok || !dashboardRes.ok) throw new Error('Failed to fetch data');

      const userData = await userRes.json();
      const dashboardData = await dashboardRes.json();

      setUser(userData);
      setUnassignedStudents(dashboardData.unassigned_students || []);
      setAllStudents(dashboardData.all_students || []);
      setTeachers(dashboardData.teachers || []);
      setActiveAssignments(dashboardData.active_assignments || []);
      setRejectedAssignments(dashboardData.rejected_assignments || []);

      if (proofsRes.ok) {
        const proofs = await proofsRes.json();
        setPendingProofsCount(proofs.length);
      }
      if (expiredRes.ok) {
        setExpiredClasses(await expiredRes.json());
      }
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleAssignStudent = async () => {
    if (!selectedTeacherForAssign) {
      toast.error('Please select a teacher');
      return;
    }
    try {
      const response = await fetch(`${API}/admin/assign-student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          student_id: selectedStudent.user_id,
          teacher_id: selectedTeacherForAssign,
          credit_price: parseFloat(customPrice)
        })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Student assigned to teacher successfully!');
      setShowAssignDialog(false);
      setSelectedStudent(null);
      setSelectedTeacherForAssign('');
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleViewTeacher = (teacher) => {
    setSelectedTeacher(teacher);
    setShowTeacherDialog(true);
  };

  const handleViewStudent = async (student) => {
    setSelectedStudent(student);
    setShowStudentDialog(true);
    try {
      const res = await fetch(`${API}/counsellor/student-profile/${student.user_id}`, { credentials: 'include' });
      if (res.ok) setStudentProfile(await res.json());
    } catch (error) {
      console.error(error);
    }
  };

  const handleReassign = async (studentId, action) => {
    try {
      const response = await fetch(`${API}/counsellor/reassign-student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ student_id: studentId, action })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success(action === 'release' ? 'Student released for reassignment' : 'Student kept with teacher');
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
      navigate('/login');
    } catch (error) { console.error(error); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-slate-600 font-medium">Loading...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-10 h-10 text-sky-500" strokeWidth={2.5} />
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Counsellor Dashboard</h1>
                <p className="text-sm text-slate-600">Manage student-teacher assignments</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-600">Counsellor</p>
                <p className="font-semibold text-slate-900">{user?.name}</p>
              </div>
              <Button onClick={handleLogout} variant="outline" className="rounded-full" data-testid="logout-button">
                <LogOut className="w-4 h-4 mr-2" /> Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-3xl p-5 text-white shadow-[4px_4px_0px_0px_rgba(14,165,233,0.3)]">
            <p className="text-sky-100 text-xs font-medium mb-1">Unassigned</p>
            <p className="text-3xl font-bold">{unassignedStudents.length}</p>
          </div>
          <div className="bg-gradient-to-br from-amber-400 to-amber-500 rounded-3xl p-5 text-white shadow-[4px_4px_0px_0px_rgba(245,158,11,0.3)]">
            <p className="text-amber-100 text-xs font-medium mb-1">Teachers</p>
            <p className="text-3xl font-bold">{teachers.length}</p>
          </div>
          <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-3xl p-5 text-white shadow-[4px_4px_0px_0px_rgba(16,185,129,0.3)]">
            <p className="text-emerald-100 text-xs font-medium mb-1">Active</p>
            <p className="text-3xl font-bold">{activeAssignments.length}</p>
          </div>
          <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-3xl p-5 text-white shadow-[4px_4px_0px_0px_rgba(239,68,68,0.3)]">
            <p className="text-red-100 text-xs font-medium mb-1">Rejected</p>
            <p className="text-3xl font-bold">{rejectedAssignments.length}</p>
          </div>
          <div className="bg-gradient-to-br from-violet-500 to-violet-600 rounded-3xl p-5 text-white shadow-[4px_4px_0px_0px_rgba(139,92,246,0.3)]">
            <p className="text-violet-100 text-xs font-medium mb-1">Pending Proofs</p>
            <p className="text-3xl font-bold">{pendingProofsCount}</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => navigate('/counsellor/proofs')} className="bg-amber-500 hover:bg-amber-600 text-white rounded-full" data-testid="proofs-link">
            <ShieldCheck className="w-4 h-4 mr-2" /> Verify Class Proofs {pendingProofsCount > 0 && `(${pendingProofsCount})`}
          </Button>
          <Button onClick={() => navigate('/demo-live-sheet')} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="demo-live-sheet-link">
            <Zap className="w-4 h-4 mr-2" /> Demo Live Sheet
          </Button>
          <Button onClick={() => navigate('/history')} className="bg-violet-500 hover:bg-violet-600 text-white rounded-full" data-testid="history-link">
            <Clock className="w-4 h-4 mr-2" /> History & Search
          </Button>
          <Button onClick={() => navigate('/counsellor/students')} variant="outline" className="rounded-full" data-testid="all-students-link">
            <Users className="w-4 h-4 mr-2" /> All Students
          </Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full" data-testid="complaints-link">
            <MessageSquare className="w-4 h-4 mr-2" /> Complaints
          </Button>
        </div>

        {/* Expired Classes Needing Reassignment */}
        {expiredClasses.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Classes Ended - Reassignment Needed</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {expiredClasses.map(cls => (
                <div key={cls.class_id} className={`rounded-2xl border-2 p-5 ${cls.can_rebook ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="flex justify-between mb-2">
                    <h3 className="font-bold text-slate-900">{cls.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${cls.can_rebook ? 'bg-amber-200 text-amber-900' : 'bg-red-200 text-red-900'}`}>
                      {cls.can_rebook ? 'Can Rebook' : 'Release Required'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mb-1">Teacher: {cls.teacher_name}</p>
                  <p className="text-xs text-slate-500 mb-3">Ended {cls.days_since_expiry} days ago</p>
                  <div className="flex gap-2">
                    {cls.can_rebook && (
                      <Button onClick={() => handleReassign(cls.assigned_student_id, 'rebook')} className="flex-1 bg-amber-500 hover:bg-amber-600 text-white rounded-full text-sm">
                        Rebook with Teacher
                      </Button>
                    )}
                    <Button onClick={() => handleReassign(cls.assigned_student_id, 'release')} variant="outline" className="flex-1 rounded-full text-sm">
                      Release Student
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rejected Assignments */}
        {rejectedAssignments.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Rejected Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rejectedAssignments.map(assignment => (
                <div key={assignment.assignment_id} className="bg-red-50 rounded-2xl border-2 border-red-200 p-5">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-bold text-slate-900">{assignment.student_name}</h3>
                      <p className="text-sm text-slate-600">Rejected by: {assignment.teacher_name}</p>
                    </div>
                    <span className="bg-red-200 text-red-900 px-3 py-1 rounded-full text-xs font-semibold">REJECTED</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unassigned Students */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-900">Available Students</h2>
          </div>
          {unassignedStudents.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">All students are assigned!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {unassignedStudents.slice(0, 6).map(student => (
                <div key={student.user_id} className="bg-white rounded-2xl border-2 border-slate-200 p-5" data-testid={`student-card-${student.user_id}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1 cursor-pointer" onClick={() => handleViewStudent(student)} data-testid={`view-student-${student.user_id}`}>
                      <h3 className="font-bold text-slate-900 hover:text-sky-600 transition-colors">{student.name}</h3>
                      <p className="text-sm text-slate-600">{student.email}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {student.institute && <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full text-xs"><MapPin className="w-3 h-3 inline mr-1" />{student.institute}</span>}
                        {student.goal && <span className="bg-sky-50 text-sky-700 px-2 py-0.5 rounded-full text-xs"><Target className="w-3 h-3 inline mr-1" />{student.goal}</span>}
                        {student.preferred_time_slot && <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full text-xs"><CalendarClock className="w-3 h-3 inline mr-1" />{student.preferred_time_slot}</span>}
                      </div>
                      <p className="text-sm text-slate-500 mt-2">Credits: {student.credits}</p>
                    </div>
                  </div>
                  <Button
                    onClick={() => { setSelectedStudent(student); setShowAssignDialog(true); }}
                    className="w-full mt-3 bg-sky-500 hover:bg-sky-600 text-white rounded-full"
                    data-testid={`assign-student-button-${student.user_id}`}
                  >
                    <UserPlus className="w-4 h-4 mr-2" /> Assign to Teacher
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Teachers List */}
        <div>
          <h2 className="text-xl font-bold text-slate-900 mb-4">Teachers</h2>
          {teachers.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">No teachers available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {teachers.map(teacher => (
                <div key={teacher.user_id} className="bg-white rounded-2xl border-2 border-slate-200 p-4 cursor-pointer hover:shadow-lg transition-all"
                  onClick={() => handleViewTeacher(teacher)} data-testid={`teacher-card-${teacher.user_id}`}>
                  <h3 className="font-bold text-slate-900">{teacher.name}</h3>
                  <p className="text-sm text-slate-600">{teacher.email}</p>
                  <p className="text-sm text-emerald-600 mt-2 font-semibold">Wallet: {teacher.credits}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Assign Student Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Assign Student to Teacher</DialogTitle>
          </DialogHeader>
          {selectedStudent && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 p-3 rounded-xl">
                <p className="font-semibold text-slate-900">{selectedStudent.name}</p>
                <p className="text-sm text-slate-600">{selectedStudent.email}</p>
              </div>
              <div>
                <Label>Select Teacher</Label>
                <select value={selectedTeacherForAssign} onChange={e => setSelectedTeacherForAssign(e.target.value)}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="teacher-select">
                  <option value="">Choose a teacher...</option>
                  {teachers.map(t => <option key={t.user_id} value={t.user_id}>{t.name}</option>)}
                </select>
              </div>
              <div>
                <Label>Credits per Class</Label>
                <Input type="number" value={customPrice} onChange={e => setCustomPrice(e.target.value)} className="rounded-xl" data-testid="custom-price-input" />
              </div>
              <Button onClick={handleAssignStudent} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="confirm-assign-button">
                Assign Student
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Teacher Profile Dialog */}
      <Dialog open={showTeacherDialog} onOpenChange={setShowTeacherDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Teacher Profile</DialogTitle>
          </DialogHeader>
          {selectedTeacher && (
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-amber-400 to-amber-500 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                    <GraduationCap className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">{selectedTeacher.name}</h3>
                    <p className="text-amber-100">{selectedTeacher.email}</p>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Wallet Balance</p>
                  <p className="text-2xl font-bold text-emerald-600">{selectedTeacher.credits}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Status</p>
                  <p className="text-2xl font-bold text-slate-900">{selectedTeacher.is_approved ? 'Approved' : 'Pending'}</p>
                </div>
              </div>
              <Button onClick={() => { setShowTeacherDialog(false); navigate(`/counsellor/teacher-schedule/${selectedTeacher.user_id}`); }}
                className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg">
                <CalendarClock className="w-5 h-5 mr-2" /> View Schedule Calendar
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Student Profile Dialog */}
      <Dialog open={showStudentDialog} onOpenChange={(open) => { setShowStudentDialog(open); if (!open) setStudentProfile(null); }}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Student Profile</DialogTitle>
          </DialogHeader>
          {selectedStudent && (
            <div className="space-y-5">
              <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                    <User className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold" data-testid="student-profile-name">{selectedStudent.name}</h3>
                    <p className="text-sky-100">{selectedStudent.email}</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Credits Balance</p>
                  <p className="text-2xl font-bold text-slate-900" data-testid="student-profile-credits">{selectedStudent.credits}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Phone</p>
                  <p className="text-lg font-semibold text-slate-900">{selectedStudent.phone || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><MapPin className="w-3 h-3 inline mr-1" />Institute</p>
                  <p className="text-lg font-semibold text-slate-900" data-testid="student-profile-institute">{selectedStudent.institute || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><Target className="w-3 h-3 inline mr-1" />Goal</p>
                  <p className="text-lg font-semibold text-slate-900" data-testid="student-profile-goal">{selectedStudent.goal || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 col-span-2">
                  <p className="text-sm text-slate-600 mb-1"><CalendarClock className="w-3 h-3 inline mr-1" />Preferred Time Slot</p>
                  <p className="text-lg font-semibold text-slate-900" data-testid="student-profile-timeslot">{selectedStudent.preferred_time_slot || 'Not provided'}</p>
                </div>
              </div>

              {/* Assignment Info */}
              {studentProfile?.current_assignment && (
                <div className="bg-emerald-50 rounded-xl p-4 border-2 border-emerald-200">
                  <p className="text-sm font-semibold text-emerald-800 mb-2">Current Assignment</p>
                  <p className="text-slate-900">Teacher: <strong>{studentProfile.current_assignment.teacher_name}</strong></p>
                  <p className="text-sm text-slate-600">Status: {studentProfile.current_assignment.status}</p>
                  <p className="text-sm text-slate-600">Price: {studentProfile.current_assignment.credit_price} credits/class</p>
                </div>
              )}

              {/* Class History */}
              {studentProfile?.class_history && studentProfile.class_history.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-slate-700 mb-2">Class History ({studentProfile.class_history.length})</p>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {studentProfile.class_history.map(cls => (
                      <div key={cls.class_id} className="bg-slate-50 rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <p className="font-medium text-slate-900 text-sm">{cls.title}</p>
                          <p className="text-xs text-slate-500">{cls.date} | {cls.start_time}-{cls.end_time}</p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${cls.is_demo ? 'bg-violet-100 text-violet-800' : 'bg-sky-100 text-sky-800'}`}>
                          {cls.is_demo ? 'Demo' : 'Class'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!studentProfile?.current_assignment && (
                <Button
                  onClick={() => { setShowStudentDialog(false); setShowAssignDialog(true); }}
                  className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-5 font-bold"
                >
                  <UserPlus className="w-5 h-5 mr-2" /> Assign to Teacher
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CounsellorDashboard;
