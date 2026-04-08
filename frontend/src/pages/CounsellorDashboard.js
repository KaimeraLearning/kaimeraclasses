import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Users, BookOpen, UserPlus } from 'lucide-react';

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
  const [loading, setLoading] = useState(true);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [customPrice, setCustomPrice] = useState('100');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/counsellor/dashboard`, { credentials: 'include' })
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
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleAssignStudent = async () => {
    if (!selectedTeacher) {
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
          teacher_id: selectedTeacher,
          credit_price: parseFloat(customPrice)
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      toast.success('Student assigned to teacher successfully!');
      setShowAssignDialog(false);
      setSelectedStudent(null);
      setSelectedTeacher('');
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      navigate('/login');
    } catch (error) {
      console.error(error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

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
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(14,165,233,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sky-100 text-sm font-medium mb-1">Unassigned Students</p>
                <p className="text-4xl font-bold">{unassignedStudents.length}</p>
              </div>
              <Users className="w-12 h-12 text-sky-200" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-amber-400 to-amber-500 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(245,158,11,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-amber-100 text-sm font-medium mb-1">Active Teachers</p>
                <p className="text-4xl font-bold">{teachers.length}</p>
              </div>
              <GraduationCap className="w-12 h-12 text-amber-200" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(16,185,129,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-emerald-100 text-sm font-medium mb-1">Active Assignments</p>
                <p className="text-4xl font-bold">{activeAssignments.length}</p>
              </div>
              <BookOpen className="w-12 h-12 text-emerald-200" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(239,68,68,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-red-100 text-sm font-medium mb-1">Rejected</p>
                <p className="text-4xl font-bold">{rejectedAssignments.length}</p>
              </div>
              <BookOpen className="w-12 h-12 text-red-200" />
            </div>
          </div>
        </div>

        {/* Rejected Assignments Panel */}
        {rejectedAssignments.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">⚠️ Rejected Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rejectedAssignments.map((assignment) => (
                <div
                  key={assignment.assignment_id}
                  className="bg-red-50 rounded-2xl border-2 border-red-200 p-6"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-bold text-slate-900">{assignment.student_name}</h3>
                      <p className="text-sm text-slate-600">→ {assignment.teacher_name}</p>
                      <p className="text-sm text-slate-500 mt-2">Price: ₹{assignment.credit_price}</p>
                    </div>
                    <span className="bg-red-200 text-red-900 px-3 py-1 rounded-full text-xs font-semibold">
                      REJECTED
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">Teacher rejected this assignment</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unassigned Students - Only show available students */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Available Students (Unassigned)</h2>
          {unassignedStudents.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">All students are assigned! 🎉</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {unassignedStudents.map((student) => (
                <div
                  key={student.user_id}
                  className="bg-white rounded-2xl border-2 border-slate-200 p-6"
                  data-testid={`student-card-${student.user_id}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-bold text-slate-900">{student.name}</h3>
                      <p className="text-sm text-slate-600">{student.email}</p>
                      <p className="text-sm text-slate-500 mt-2">Credits: {student.credits}</p>
                    </div>
                  </div>
                  <Button
                    onClick={() => {
                      setSelectedStudent(student);
                      setShowAssignDialog(true);
                    }}
                    className="w-full mt-4 bg-sky-500 hover:bg-sky-600 text-white rounded-full"
                    data-testid={`assign-student-button-${student.user_id}`}
                  >
                    <UserPlus className="w-4 h-4 mr-2" />
                    Assign to Teacher
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Teachers List */}
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Teachers</h2>
          {teachers.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">No teachers available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {teachers.map((teacher) => (
                <div
                  key={teacher.user_id}
                  className="bg-white rounded-2xl border-2 border-slate-200 p-4"
                  data-testid={`teacher-card-${teacher.user_id}`}
                >
                  <h3 className="font-bold text-slate-900">{teacher.name}</h3>
                  <p className="text-sm text-slate-600">{teacher.email}</p>
                  <p className="text-sm text-emerald-600 mt-2 font-semibold">Wallet: ₹{teacher.credits}</p>
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
            <DialogTitle className="text-2xl font-bold text-slate-900">
              Assign Student to Teacher
            </DialogTitle>
          </DialogHeader>
          {selectedStudent && (
            <div className="space-y-4 mt-4">
              <div>
                <Label>Student</Label>
                <div className="bg-slate-50 p-3 rounded-xl">
                  <p className="font-semibold text-slate-900">{selectedStudent.name}</p>
                  <p className="text-sm text-slate-600">{selectedStudent.email}</p>
                </div>
              </div>

              <div>
                <Label>Select Teacher</Label>
                <select
                  value={selectedTeacher}
                  onChange={(e) => setSelectedTeacher(e.target.value)}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"
                  data-testid="teacher-select"
                >
                  <option value="">Choose a teacher...</option>
                  {teachers.map((teacher) => (
                    <option key={teacher.user_id} value={teacher.user_id}>
                      {teacher.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label>Credits per Class (for this student)</Label>
                <Input
                  type="number"
                  value={customPrice}
                  onChange={(e) => setCustomPrice(e.target.value)}
                  className="rounded-xl"
                  data-testid="custom-price-input"
                />
              </div>

              <Button
                onClick={handleAssignStudent}
                className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold"
                data-testid="confirm-assign-button"
              >
                Assign Student
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CounsellorDashboard;
