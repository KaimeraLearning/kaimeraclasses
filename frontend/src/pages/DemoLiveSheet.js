import { getApiError } from '../utils/api';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, Users, Calendar, Clock, Phone, Mail, Building, CheckCircle2, UserPlus, Loader2, RefreshCw, Zap } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DemoLiveSheet = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [demos, setDemos] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acceptingId, setAcceptingId] = useState(null);
  const [assigningId, setAssigningId] = useState(null);
  const [selectedTeacher, setSelectedTeacher] = useState({});

  const fetchData = useCallback(async () => {
    try {
      const [userRes, sheetRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/demo/live-sheet`, { credentials: 'include' })
      ]);
      if (!userRes.ok) { navigate('/login'); return; }
      const userData = await userRes.json();
      setUser(userData);

      if (sheetRes.ok) {
        const data = await sheetRes.json();
        setDemos(data.demos || []);
        setTeachers(data.teachers || []);
      }
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAccept = async (demoId) => {
    setAcceptingId(demoId);
    try {
      const res = await fetch(`${API}/demo/accept/${demoId}`, {
        method: 'POST', credentials: 'include'
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      toast.success(data.message);
      if (data.student_credentials) {
        toast.info(`New student created: ${data.student_credentials.email} / ${data.student_credentials.temp_password}`, { duration: 10000 });
      }
      fetchData();
    } catch (err) { toast.error(err.message); }
    finally { setAcceptingId(null); }
  };

  const handleAssign = async (demoId) => {
    const teacherId = selectedTeacher[demoId];
    if (!teacherId) { toast.error('Select a teacher first'); return; }
    setAssigningId(demoId);
    try {
      const res = await fetch(`${API}/demo/assign`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ demo_id: demoId, teacher_id: teacherId })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      toast.success(data.message);
      fetchData();
    } catch (err) { toast.error(err.message); }
    finally { setAssigningId(null); }
  };

  const backPath = user?.role === 'teacher' ? '/teacher-dashboard'
    : user?.role === 'counsellor' ? '/counsellor-dashboard'
    : '/admin-dashboard';

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50">
      {/* Header */}
      <div className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate(backPath)} className="rounded-full" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2" style={{ fontFamily: 'Fredoka, sans-serif' }}>
                <Zap className="w-5 h-5 text-amber-500" />
                Demo Live Sheet
              </h1>
              <p className="text-xs text-slate-500">{demos.length} pending demo request{demos.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <Button onClick={fetchData} variant="outline" className="rounded-full border-2 border-slate-200" data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {demos.length === 0 ? (
          <div className="text-center py-20">
            <Users className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-600 mb-2">No Pending Demos</h3>
            <p className="text-slate-400">New demo requests will appear here in real-time</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {demos.map(demo => (
              <div key={demo.demo_id} className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden hover:-translate-y-1 transition-all duration-200" data-testid={`demo-card-${demo.demo_id}`}>
                {/* Card header */}
                <div className="bg-gradient-to-r from-sky-500 to-violet-500 px-6 py-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-white font-bold text-lg truncate">{demo.name}</h3>
                    <span className="bg-white/20 text-white text-xs font-medium px-3 py-1 rounded-full">
                      Demo #{demo.demo_number || '?'}
                    </span>
                  </div>
                </div>

                {/* Card body */}
                <div className="px-6 py-5 space-y-3">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Mail className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span className="truncate">{demo.email}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Phone className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span>{demo.phone}</span>
                  </div>
                  {demo.institute && (
                    <div className="flex items-center gap-2 text-sm text-slate-600">
                      <Building className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      <span className="truncate">{demo.institute}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                      <Calendar className="w-4 h-4 text-sky-500" />
                      <span>{demo.preferred_date}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                      <Clock className="w-4 h-4 text-amber-500" />
                      <span>{demo.preferred_time_slot}</span>
                    </div>
                  </div>
                  {demo.age && (
                    <p className="text-xs text-slate-400">Age: {demo.age}</p>
                  )}
                  {demo.message && (
                    <p className="text-xs text-slate-500 bg-slate-50 rounded-xl p-3 italic">"{demo.message}"</p>
                  )}
                </div>

                {/* Card actions */}
                <div className="px-6 pb-5 space-y-3">
                  {user?.role === 'teacher' && (
                    <Button
                      onClick={() => handleAccept(demo.demo_id)}
                      disabled={acceptingId === demo.demo_id}
                      className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold shadow-[0_4px_14px_0_rgba(16,185,129,0.39)]"
                      data-testid={`accept-demo-${demo.demo_id}`}
                    >
                      {acceptingId === demo.demo_id ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                      )}
                      Accept Demo
                    </Button>
                  )}

                  {user?.role && ['counsellor', 'admin'].includes(user.role) && (
                    <div className="space-y-2">
                      <select
                        value={selectedTeacher[demo.demo_id] || ''}
                        onChange={e => setSelectedTeacher(prev => ({...prev, [demo.demo_id]: e.target.value}))}
                        className="w-full bg-slate-50 border-2 border-slate-200 rounded-xl h-10 px-3 text-sm"
                        data-testid={`assign-teacher-select-${demo.demo_id}`}
                      >
                        <option value="">Select teacher to assign...</option>
                        {teachers.map(t => (
                          <option key={t.user_id} value={t.user_id}>{t.name} ({t.email})</option>
                        ))}
                      </select>
                      <Button
                        onClick={() => handleAssign(demo.demo_id)}
                        disabled={assigningId === demo.demo_id || !selectedTeacher[demo.demo_id]}
                        className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full font-bold shadow-[0_4px_14px_0_rgba(14,165,233,0.39)]"
                        data-testid={`assign-demo-${demo.demo_id}`}
                      >
                        {assigningId === demo.demo_id ? (
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        ) : (
                          <UserPlus className="w-4 h-4 mr-2" />
                        )}
                        Assign to Teacher
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DemoLiveSheet;
