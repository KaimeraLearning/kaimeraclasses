import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Users, BookOpen } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CounsellorDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);

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
      setStudents(dashboardData.students || []);
      setTeachers(dashboardData.teachers || []);
      setAssignments(dashboardData.assignments || []);
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load dashboard');
      setLoading(false);
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(14,165,233,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sky-100 text-sm font-medium mb-1">Total Students</p>
                <p className="text-4xl font-bold">{students.length}</p>
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
                <p className="text-4xl font-bold">{assignments.length}</p>
              </div>
              <BookOpen className="w-12 h-12 text-emerald-200" />
            </div>
          </div>
        </div>

        {/* Coming Soon Message */}
        <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
          <BookOpen className="w-16 h-16 text-sky-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Phase 1: Foundation Complete</h2>
          <p className="text-slate-600 mb-4">
            Counsellor role has been created. Demo assignment features coming in Phase 2!
          </p>
          <div className="bg-slate-50 rounded-2xl p-6 mt-6 text-left max-w-2xl mx-auto">
            <h3 className="font-bold text-slate-900 mb-3">✅ Phase 1 Complete:</h3>
            <ul className="space-y-2 text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold">✓</span>
                <span>Counsellor role added to system</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold">✓</span>
                <span>Students can only self-register (0 credits)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold">✓</span>
                <span>Admin can create teacher & counsellor accounts</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold">✓</span>
                <span>System pricing configuration ready</span>
              </li>
            </ul>
            <h3 className="font-bold text-slate-900 mb-3 mt-6">🔄 Phase 2 Next:</h3>
            <ul className="space-y-2 text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-sky-500 font-bold">→</span>
                <span>Demo request system</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-sky-500 font-bold">→</span>
                <span>Teacher availability management</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-sky-500 font-bold">→</span>
                <span>Counsellor assignment workflow</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CounsellorDashboard;
