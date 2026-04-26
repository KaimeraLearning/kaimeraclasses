import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { ArrowLeft, Search, User, GraduationCap, Clock, BookOpen, FileText, MessageSquare, Star, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';

import { API } from '../utils/api';

const HistoryPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [users, setUsers] = useState({ students: [], teachers: [] });
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});

  const fetchUsers = useCallback(async () => {
    try {
      const [userRes, usersRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/history/users`, { credentials: 'include' })
      ]);
      if (!userRes.ok) { navigate('/login'); return; }
      setUser(await userRes.json());
      if (usersRes.ok) setUsers(await usersRes.json());
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`${API}/history/search?q=${encodeURIComponent(searchQuery)}`, { credentials: 'include' });
      if (res.ok) setSearchResults(await res.json());
    } catch { toast.error('Search failed'); }
  };

  const loadProfile = async (userId, role) => {
    setProfileLoading(true);
    setSelectedProfile({ userId, role });
    setExpandedSections({});
    try {
      const endpoint = role === 'teacher' ? 'teacher' : 'student';
      const res = await fetch(`${API}/history/${endpoint}/${userId}`, { credentials: 'include' });
      if (res.ok) setProfileData(await res.json());
      else toast.error('Failed to load profile');
    } catch { toast.error('Error loading profile'); }
    finally { setProfileLoading(false); }
  };

  const toggleSection = (key) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const formatDate = (d) => {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
    catch { return d; }
  };

  const actionColors = {
    demo_requested: 'bg-sky-100 text-sky-700',
    demo_accepted: 'bg-emerald-100 text-emerald-700',
    demo_assigned: 'bg-violet-100 text-violet-700',
    demo_feedback_submitted: 'bg-amber-100 text-amber-700',
    demo_extra_granted: 'bg-rose-100 text-rose-700'
  };

  const backPath = user?.role === 'admin' ? '/admin-dashboard' : '/counsellor-dashboard';

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
    </div>
  );

  const SectionBlock = ({ title, icon: Icon, items, renderItem, sectionKey }) => {
    const isOpen = expandedSections[sectionKey] !== false;
    return (
      <div className="bg-white rounded-2xl border-2 border-slate-100 overflow-hidden">
        <button onClick={() => toggleSection(sectionKey)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors" data-testid={`toggle-${sectionKey}`}>
          <div className="flex items-center gap-3">
            <Icon className="w-5 h-5 text-sky-500" />
            <span className="font-semibold text-slate-800">{title}</span>
            <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-0.5 rounded-full">{items.length}</span>
          </div>
          {isOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </button>
        {isOpen && items.length > 0 && (
          <div className="px-5 pb-4 space-y-2">
            {items.map((item, i) => renderItem(item, i))}
          </div>
        )}
        {isOpen && items.length === 0 && (
          <p className="px-5 pb-4 text-sm text-slate-400">No records</p>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50">
      {/* Header */}
      <div className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate(backPath)} className="rounded-full" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>History & Search</h1>
            <p className="text-xs text-slate-500">Complete student/teacher activity history</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: User list + search */}
          <div className="lg:col-span-1 space-y-6">
            {/* Search */}
            <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Search className="w-4 h-4 text-sky-500" /> Search Logs
              </h3>
              <div className="flex gap-2">
                <Input
                  placeholder="Name, email, or action..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  className="bg-slate-50 border-2 border-slate-200 rounded-xl text-sm"
                  data-testid="history-search-input"
                />
                <Button onClick={handleSearch} className="bg-sky-500 hover:bg-sky-600 text-white rounded-xl px-4" data-testid="history-search-btn">
                  <Search className="w-4 h-4" />
                </Button>
              </div>
              {searchResults.length > 0 && (
                <div className="mt-4 max-h-60 overflow-y-auto space-y-2">
                  {searchResults.slice(0, 20).map((log, i) => (
                    <div key={i} className="text-xs p-2 bg-slate-50 rounded-lg">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mr-2 ${actionColors[log.action] || 'bg-slate-100 text-slate-600'}`}>
                        {log.action?.replace(/_/g, ' ')}
                      </span>
                      <p className="text-slate-600 mt-1">{log.details}</p>
                      <p className="text-slate-400 mt-0.5">{formatDate(log.created_at)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Students list */}
            <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-amber-500" /> Students ({users.students.length})
              </h3>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {users.students.map(s => (
                  <button
                    key={s.user_id}
                    onClick={() => loadProfile(s.user_id, 'student')}
                    className={`w-full text-left px-3 py-2 rounded-xl text-sm transition-colors ${
                      selectedProfile?.userId === s.user_id ? 'bg-sky-50 text-sky-700 font-medium' : 'hover:bg-slate-50 text-slate-700'
                    }`}
                    data-testid={`student-${s.user_id}`}
                  >
                    {s.name} <span className="text-xs text-slate-400">({s.email})</span>
                  </button>
                ))}
                {users.students.length === 0 && <p className="text-sm text-slate-400">No students</p>}
              </div>
            </div>

            {/* Teachers list */}
            <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-violet-500" /> Teachers ({users.teachers.length})
              </h3>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {users.teachers.map(t => (
                  <button
                    key={t.user_id}
                    onClick={() => loadProfile(t.user_id, 'teacher')}
                    className={`w-full text-left px-3 py-2 rounded-xl text-sm transition-colors ${
                      selectedProfile?.userId === t.user_id ? 'bg-sky-50 text-sky-700 font-medium' : 'hover:bg-slate-50 text-slate-700'
                    }`}
                    data-testid={`teacher-${t.user_id}`}
                  >
                    {t.name} <span className="text-xs text-slate-400">({t.email})</span>
                  </button>
                ))}
                {users.teachers.length === 0 && <p className="text-sm text-slate-400">No teachers</p>}
              </div>
            </div>
          </div>

          {/* Right: Profile detail */}
          <div className="lg:col-span-2">
            {!selectedProfile ? (
              <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-12 text-center">
                <Search className="w-16 h-16 text-slate-200 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-600 mb-2">Select a Profile</h3>
                <p className="text-slate-400">Click on a student or teacher to view their complete history</p>
              </div>
            ) : profileLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
              </div>
            ) : profileData ? (
              <div className="space-y-4">
                {/* Profile header */}
                <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-sky-400 to-violet-500 rounded-2xl flex items-center justify-center text-white font-bold text-xl">
                      {(profileData.student || profileData.teacher)?.name?.charAt(0)?.toUpperCase()}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>
                        {(profileData.student || profileData.teacher)?.name}
                      </h2>
                      <p className="text-sm text-slate-500">{(profileData.student || profileData.teacher)?.email}</p>
                      <div className="flex gap-2 mt-1">
                        <span className="bg-sky-100 text-sky-700 text-xs font-medium px-2 py-0.5 rounded-full">
                          {(profileData.student || profileData.teacher)?.role}
                        </span>
                        {profileData.student?.institute && (
                          <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full">{profileData.student.institute}</span>
                        )}
                        {profileData.student?.credits !== undefined && (
                          <span className="bg-amber-100 text-amber-700 text-xs font-medium px-2 py-0.5 rounded-full">
                            {profileData.student.credits} credits
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Demos */}
                <SectionBlock
                  title="Demo Sessions"
                  icon={Star}
                  sectionKey="demos"
                  items={profileData.demos || []}
                  renderItem={(d, i) => (
                    <div key={i} className="bg-slate-50 rounded-xl p-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-800">Demo #{d.demo_number || i + 1}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          d.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' :
                          d.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                          d.status === 'feedback_submitted' ? 'bg-violet-100 text-violet-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>{d.status}</span>
                      </div>
                      <p className="text-slate-500 mt-1">{d.preferred_date} at {d.preferred_time_slot}</p>
                      {d.accepted_by_teacher_name && <p className="text-slate-500">Teacher: {d.accepted_by_teacher_name}</p>}
                    </div>
                  )}
                />

                {/* Assignments */}
                <SectionBlock
                  title="Assignments"
                  icon={BookOpen}
                  sectionKey="assignments"
                  items={profileData.assignments || []}
                  renderItem={(a, i) => (
                    <div key={i} className="bg-slate-50 rounded-xl p-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-800">
                          {selectedProfile?.role === 'student' ? a.teacher_name : a.student_name}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          a.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                          a.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                          a.status === 'rejected' ? 'bg-red-100 text-red-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>{a.status}</span>
                      </div>
                      <p className="text-slate-500 mt-1">Price: {a.credit_price} credits</p>
                    </div>
                  )}
                />

                {/* Classes */}
                <SectionBlock
                  title="Classes"
                  icon={BookOpen}
                  sectionKey="classes"
                  items={profileData.classes || []}
                  renderItem={(c, i) => (
                    <div key={i} className="bg-slate-50 rounded-xl p-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-800">{c.title}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          c.status === 'scheduled' ? 'bg-sky-100 text-sky-700' :
                          c.status === 'in_progress' ? 'bg-emerald-100 text-emerald-700' :
                          c.status === 'completed' ? 'bg-slate-100 text-slate-600' :
                          'bg-red-100 text-red-700'
                        }`}>{c.status}</span>
                      </div>
                      <p className="text-slate-500 mt-1">{c.date} to {c.end_date || c.date} | {c.start_time} - {c.end_time}</p>
                      {c.is_demo && <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">Demo</span>}
                    </div>
                  )}
                />

                {/* Complaints (student only) */}
                {profileData.complaints && (
                  <SectionBlock
                    title="Complaints"
                    icon={MessageSquare}
                    sectionKey="complaints"
                    items={profileData.complaints || []}
                    renderItem={(c, i) => (
                      <div key={i} className="bg-slate-50 rounded-xl p-3 text-sm">
                        <p className="font-medium text-slate-800">{c.subject}</p>
                        <p className="text-slate-500 mt-1 truncate">{c.description}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === 'resolved' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                          {c.status}
                        </span>
                      </div>
                    )}
                  />
                )}

                {/* Feedback (student only) */}
                {profileData.feedbacks && (
                  <SectionBlock
                    title="Demo Feedback"
                    icon={FileText}
                    sectionKey="feedbacks"
                    items={profileData.feedbacks || []}
                    renderItem={(f, i) => (
                      <div key={i} className="bg-slate-50 rounded-xl p-3 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-800">Rating: {f.rating}/5</span>
                          <span className="text-xs text-slate-500">for {f.teacher_name}</span>
                        </div>
                        <p className="text-slate-500 mt-1">{f.feedback_text}</p>
                      </div>
                    )}
                  />
                )}

                {/* Activity log */}
                <SectionBlock
                  title="Activity Timeline"
                  icon={Clock}
                  sectionKey="logs"
                  items={profileData.logs || []}
                  renderItem={(log, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <div className="w-2 h-2 mt-2 rounded-full bg-sky-400 flex-shrink-0" />
                      <div>
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${actionColors[log.action] || 'bg-slate-100 text-slate-600'}`}>
                          {log.action?.replace(/_/g, ' ')}
                        </span>
                        <p className="text-slate-600 mt-0.5">{log.details}</p>
                        <p className="text-slate-400 text-xs">{formatDate(log.created_at)}</p>
                      </div>
                    </div>
                  )}
                />
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
