import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Plus, Calendar, Users, AlertCircle } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeacherDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [classes, setClasses] = useState([]);
  const [pendingAssignments, setPendingAssignments] = useState([]);
  const [approvedStudents, setApprovedStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    class_type: '1:1',
    date: '',
    start_time: '',
    end_time: '',
    credits_required: '',
    max_students: ''
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/teacher/dashboard`, { credentials: 'include' })
      ]);

      if (!userRes.ok || !dashboardRes.ok) throw new Error('Failed to fetch data');

      const userData = await userRes.json();
      const dashboardData = await dashboardRes.json();

      setUser(userData);
      setClasses(dashboardData.classes);
      setPendingAssignments(dashboardData.pending_assignments || []);
      setApprovedStudents(dashboardData.approved_students || []);
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API}/classes/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          ...formData,
          credits_required: parseFloat(formData.credits_required),
          max_students: parseInt(formData.max_students)
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      toast.success('Class created successfully!');
      setShowCreateDialog(false);
      setFormData({
        title: '',
        subject: '',
        class_type: '1:1',
        date: '',
        start_time: '',
        end_time: '',
        credits_required: '',
        max_students: ''
      });
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

  const handleApproveAssignment = async (assignmentId, approved) => {
    try {
      const response = await fetch(`${API}/teacher/approve-assignment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          assignment_id: assignmentId,
          approved
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      toast.success(approved ? 'Student approved!' : 'Student rejected');
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleDeleteClass = async (classId) => {
    if (!window.confirm('Are you sure you want to delete this class?')) return;

    try {
      const response = await fetch(`${API}/classes/delete/${classId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      toast.success('Class deleted successfully');
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
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

  if (!user?.is_approved) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center" data-testid="teacher-pending-approval">
        <div className="bg-white rounded-3xl p-12 border-2 border-amber-200 max-w-md text-center">
          <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Approval Pending</h2>
          <p className="text-slate-600 mb-6">
            Your teacher account is awaiting admin approval. You'll be able to create classes once approved.
          </p>
          <Button onClick={handleLogout} className="rounded-full" data-testid="logout-button">
            Logout
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-10 h-10 text-sky-500" strokeWidth={2.5} />
              <h1 className="text-2xl font-bold text-slate-900">Teacher Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-600">Welcome,</p>
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
        {/* Pending Student Assignments */}
        {pendingAssignments.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Pending Student Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingAssignments.map((assignment) => (
                <div
                  key={assignment.assignment_id}
                  className="bg-amber-50 rounded-2xl border-2 border-amber-200 p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-bold text-slate-900">{assignment.student_name}</h3>
                      <p className="text-sm text-slate-600">{assignment.student_email}</p>
                      <p className="text-sm text-slate-500 mt-2">
                        Credits per class: ₹{assignment.credit_price}
                      </p>
                    </div>
                    <span className="bg-amber-200 text-amber-900 px-3 py-1 rounded-full text-xs font-semibold">
                      PENDING
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleApproveAssignment(assignment.assignment_id, true)}
                      className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full"
                    >
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleApproveAssignment(assignment.assignment_id, false)}
                      variant="outline"
                      className="flex-1 rounded-full"
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Approved Students */}
        {approvedStudents.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">My Students</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {approvedStudents.map((assignment) => (
                <div
                  key={assignment.assignment_id}
                  className="bg-emerald-50 rounded-2xl border-2 border-emerald-200 p-4"
                >
                  <h3 className="font-bold text-slate-900">{assignment.student_name}</h3>
                  <p className="text-xs text-slate-600">{assignment.student_email}</p>
                  <p className="text-sm text-emerald-600 mt-2 font-semibold">
                    ₹{assignment.credit_price}/class
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-8">
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6 py-3 font-bold"
            data-testid="create-class-button"
          >
            <Plus className="w-5 h-5 mr-2" />
            Create New Class
          </Button>
        </div>

        <h2 className="text-2xl font-bold text-slate-900 mb-4">My Classes</h2>
        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <p className="text-slate-600">No classes created yet. Create your first class!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classes.map((cls) => (
              <div
                key={cls.class_id}
                className="bg-white rounded-3xl border-2 border-slate-200 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] p-6"
                data-testid={`class-card-${cls.class_id}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">
                    {cls.subject}
                  </span>
                  <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-xs font-semibold">
                    {cls.status}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-slate-900 mb-4">{cls.title}</h3>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-slate-600">
                    <Calendar className="w-4 h-4" />
                    <span className="text-sm">{format(parseISO(cls.date), 'MMM dd, yyyy')}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Users className="w-4 h-4" />
                    <span className="text-sm">{cls.enrolled_students.length} / {cls.max_students} students</span>
                  </div>
                </div>

                {cls.status === 'scheduled' && (
                  <div className="space-y-2">
                    <Button
                      onClick={() => navigate(`/class/${cls.class_id}`)}
                      className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold"
                      data-testid={`start-class-button-${cls.class_id}`}
                    >
                      Start Class
                    </Button>
                    <Button
                      onClick={() => handleDeleteClass(cls.class_id)}
                      variant="outline"
                      className="w-full border-2 border-red-200 hover:bg-red-50 text-red-600 rounded-full font-bold"
                      data-testid={`delete-class-button-${cls.class_id}`}
                    >
                      Delete Class
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Create New Class</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateClass} className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Title</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-title-input"
                />
              </div>
              <div>
                <Label>Subject</Label>
                <Input
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-subject-input"
                />
              </div>
              <div>
                <Label>Type</Label>
                <select
                  value={formData.class_type}
                  onChange={(e) => setFormData({ ...formData, class_type: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"
                  data-testid="class-type-select"
                >
                  <option value="1:1">1:1</option>
                  <option value="group">Group</option>
                </select>
              </div>
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-date-input"
                />
              </div>
              <div>
                <Label>Start Time</Label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-start-time-input"
                />
              </div>
              <div>
                <Label>End Time</Label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-end-time-input"
                />
              </div>
              <div>
                <Label>Credits Required</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={formData.credits_required}
                  onChange={(e) => setFormData({ ...formData, credits_required: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-credits-input"
                />
              </div>
              <div>
                <Label>Max Students</Label>
                <Input
                  type="number"
                  value={formData.max_students}
                  onChange={(e) => setFormData({ ...formData, max_students: e.target.value })}
                  className="rounded-xl"
                  required
                  data-testid="class-max-students-input"
                />
              </div>
            </div>
            <Button
              type="submit"
              className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold"
              data-testid="submit-create-class-button"
            >
              Create Class
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TeacherDashboard;
