import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  GraduationCap, LogOut, Check, X, DollarSign, MessageSquare, UserPlus, Copy, Zap,
  History, Search, Shield, Award, Filter, BookOpen, KeyRound, Users, Trash2, Plus,
  Ban, ChevronDown, ChevronUp, Calendar, CreditCard, BarChart3, Play, Settings, Save, Pencil
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

// ─── Reusable Sub-Components ───

const RoleBadge = ({ role }) => {
  const colors = { admin: 'bg-red-100 text-red-700', teacher: 'bg-amber-100 text-amber-700', student: 'bg-sky-100 text-sky-700', counsellor: 'bg-violet-100 text-violet-700' };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${colors[role] || 'bg-slate-100 text-slate-700'}`}>{role}</span>;
};

const StatCard = ({ label, value, color = 'slate' }) => (
  <div className={`bg-${color}-50 rounded-xl p-3 text-center`}>
    <p className={`text-xs text-${color}-600`}>{label}</p>
    <p className={`text-2xl font-bold text-${color}-700`}>{value}</p>
  </div>
);

// ─── Main Component ───

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mainTab, setMainTab] = useState('users');

  // Data stores
  const [allUsers, setAllUsers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [dailyRevenue, setDailyRevenue] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [pendingProofs, setPendingProofs] = useState([]);
  const [badgeTemplates, setBadgeTemplates] = useState([]);
  const [counsellorTracking, setCounsellorTracking] = useState([]);
  const [counsellorDailyStats, setCounsellorDailyStats] = useState({});

  // Identity Creator
  const [createRole, setCreateRole] = useState('student');
  const [createForm, setCreateForm] = useState({ name: '', email: '', password: '', phone: '', institute: '', goal: '', preferred_time_slot: '', state: '', city: '', country: '', grade: '' });
  const [credsResult, setCredsResult] = useState(null);

  // Staff Directory
  const [staffSearch, setStaffSearch] = useState('');
  const [staffRoleFilter, setStaffRoleFilter] = useState('all');
  const [drawerUser, setDrawerUser] = useState(null);
  const [drawerData, setDrawerData] = useState(null);

  // Transactions
  const [txnSearch, setTxnSearch] = useState('');
  const [txnRoleFilter, setTxnRoleFilter] = useState('all');
  const [txnDateFrom, setTxnDateFrom] = useState('');
  const [txnDateTo, setTxnDateTo] = useState('');
  const [txnView, setTxnView] = useState('daily');

  // Proofs
  const [proofDateFrom, setProofDateFrom] = useState('');
  const [proofDateTo, setProofDateTo] = useState('');

  // Badges
  const [badgeTarget, setBadgeTarget] = useState('');
  const [badgeName, setBadgeName] = useState('');
  const [selectedTemplateBadge, setSelectedTemplateBadge] = useState('');
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateDesc, setNewTemplateDesc] = useState('');

  // Credits
  const [creditsDialog, setCreditsDialog] = useState(false);
  const [creditUser, setCreditUser] = useState(null);
  const [creditAmount, setCreditAmount] = useState('');
  const [creditAction, setCreditAction] = useState('add');

  // Password Reset
  const [resetEmail, setResetEmail] = useState('');
  const [resetPassword, setResetPassword] = useState('');

  // Classes
  const [classFilter, setClassFilter] = useState({ search: '', is_demo: '', status: '' });

  // Counsellor chart
  const [expandedCounsellor, setExpandedCounsellor] = useState(null);

  // System Pricing
  const [pricingForm, setPricingForm] = useState({ demo_price_student: '', class_price_student: '', demo_earning_teacher: '', class_earning_teacher: '' });
  const [pricingLoaded, setPricingLoaded] = useState(false);

  // Student Edit
  const [editingStudent, setEditingStudent] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [userRes, usersRes, classesRes, txnRes, dailyRes, complaintsRes, proofsRes, tmplRes, trackRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/admin/all-users`, { credentials: 'include' }),
        fetch(`${API}/admin/classes`, { credentials: 'include' }),
        fetch(`${API}/admin/transactions`, { credentials: 'include' }),
        fetch(`${API}/admin/transactions?view=daily`, { credentials: 'include' }),
        fetch(`${API}/admin/complaints`, { credentials: 'include' }),
        fetch(`${API}/admin/approved-proofs`, { credentials: 'include' }),
        fetch(`${API}/admin/badge-templates`, { credentials: 'include' }),
        fetch(`${API}/admin/counsellor-tracking`, { credentials: 'include' })
      ]);
      if (!userRes.ok) throw new Error();
      setUser(await userRes.json());
      if (usersRes.ok) setAllUsers(await usersRes.json());
      if (classesRes.ok) setClasses(await classesRes.json());
      if (txnRes.ok) setTransactions(await txnRes.json());
      if (dailyRes.ok) setDailyRevenue(await dailyRes.json());
      if (complaintsRes.ok) setComplaints(await complaintsRes.json());
      if (proofsRes.ok) setPendingProofs(await proofsRes.json());
      if (tmplRes.ok) setBadgeTemplates(await tmplRes.json());
      if (trackRes.ok) setCounsellorTracking(await trackRes.json());
    } catch { toast.error('Failed to load dashboard'); }
    setLoading(false);
  };

  // ─── Handlers ───

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!createForm.name || !createForm.email || !createForm.password) { toast.error('Name, email and password required'); return; }
    try {
      const body = { ...createForm, role: createRole };
      const res = await fetch(`${API}/admin/create-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      const data = await res.json();
      toast.success(data.message);
      setCredsResult(data.credentials);
      setCreateForm({ name: '', email: '', password: '', phone: '', institute: '', goal: '', preferred_time_slot: '', state: '', city: '', country: '', grade: '' });
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleOpenDrawer = async (userId) => {
    setDrawerData(null);
    const u = allUsers.find(x => x.user_id === userId);
    setDrawerUser(u);
    try {
      const res = await fetch(`${API}/admin/user-detail/${userId}`, { credentials: 'include' });
      if (res.ok) setDrawerData(await res.json());
    } catch {}
  };

  const handleBlock = async (userId, blocked) => {
    if (!window.confirm(`${blocked ? 'Block' : 'Unblock'} this user?`)) return;
    try {
      const res = await fetch(`${API}/admin/block-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, blocked })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success(data.message || `User ${blocked ? 'blocked' : 'unblocked'}`);
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('PERMANENTLY delete this user?')) return;
    try {
      const res = await fetch(`${API}/admin/delete-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('User deleted');
      setDrawerUser(null);
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleResetPassword = async () => {
    if (!resetEmail || !resetPassword) { toast.error('Email and new password required'); return; }
    try {
      const res = await fetch(`${API}/admin/reset-password`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resetEmail, new_password: resetPassword })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Password reset!');
      setResetEmail('');
      setResetPassword('');
    } catch (err) { toast.error(err.message); }
  };

  const handleAdjustCredits = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/admin/adjust-credits`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: creditUser, amount: parseFloat(creditAmount), action: creditAction })
      });
      if (!res.ok) throw new Error();
      toast.success('Credits adjusted');
      setCreditsDialog(false);
      fetchAll();
    } catch { toast.error('Failed to adjust credits'); }
  };

  const handleApproveProof = async (proofId, approved) => {
    const notes = approved ? '' : (prompt('Reason for rejection:') || '');
    try {
      const res = await fetch(`${API}/admin/approve-proof`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof_id: proofId, approved, admin_notes: notes })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success(approved ? 'Proof approved & teacher credited!' : 'Proof rejected');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleCreateBadgeTemplate = async () => {
    if (!newTemplateName.trim()) { toast.error('Badge name required'); return; }
    try {
      const res = await fetch(`${API}/admin/badge-template`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTemplateName.trim(), description: newTemplateDesc })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Template created');
      setNewTemplateName('');
      setNewTemplateDesc('');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleDeleteBadgeTemplate = async (id) => {
    await fetch(`${API}/admin/badge-template/${id}`, { method: 'DELETE', credentials: 'include' });
    fetchAll();
  };

  const handleAssignBadge = async () => {
    const badge = selectedTemplateBadge || badgeName;
    if (!badgeTarget || !badge) { toast.error('Select user and badge'); return; }
    try {
      const res = await fetch(`${API}/admin/assign-badge`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: badgeTarget, badge_name: badge })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Badge assigned');
      setBadgeName('');
      setSelectedTemplateBadge('');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleFilterTransactions = async () => {
    const params = new URLSearchParams();
    if (txnRoleFilter !== 'all') params.set('role', txnRoleFilter);
    if (txnDateFrom) params.set('date_from', txnDateFrom);
    if (txnDateTo) params.set('date_to', txnDateTo);
    if (txnSearch) params.set('search', txnSearch);
    if (txnView === 'daily') params.set('view', 'daily');
    try {
      const res = await fetch(`${API}/admin/transactions?${params}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        if (txnView === 'daily') setDailyRevenue(data);
        else setTransactions(data);
      }
    } catch {}
  };

  const handleApproveTeacher = async (teacherId, approved) => {
    try {
      await fetch(`${API}/admin/approve-teacher`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: teacherId, approved })
      });
      toast.success(approved ? 'Teacher approved' : 'Teacher rejected');
      fetchAll();
    } catch {}
  };

  const fetchCounsellorDailyStats = async (cid) => {
    if (expandedCounsellor === cid) { setExpandedCounsellor(null); return; }
    setExpandedCounsellor(cid);
    try {
      const res = await fetch(`${API}/admin/counsellor-daily-stats/${cid}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCounsellorDailyStats(prev => ({ ...prev, [cid]: data }));
      }
    } catch {}
  };

  const handleLogout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
    navigate('/login');
  };

  const fetchPricing = async () => {
    try {
      const res = await fetch(`${API}/admin/get-pricing`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setPricingForm({
          demo_price_student: data.demo_price_student ?? '',
          class_price_student: data.class_price_student ?? '',
          demo_earning_teacher: data.demo_earning_teacher ?? '',
          class_earning_teacher: data.class_earning_teacher ?? ''
        });
        setPricingLoaded(true);
      }
    } catch {}
  };

  const handleSavePricing = async () => {
    try {
      const res = await fetch(`${API}/admin/set-pricing`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          demo_price_student: parseFloat(pricingForm.demo_price_student) || 0,
          class_price_student: parseFloat(pricingForm.class_price_student) || 0,
          demo_earning_teacher: parseFloat(pricingForm.demo_earning_teacher) || 0,
          class_earning_teacher: parseFloat(pricingForm.class_earning_teacher) || 0
        })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('System pricing updated!');
    } catch (err) { toast.error(err.message); }
  };

  const handleStartEditStudent = () => {
    if (!drawerUser || drawerUser.role !== 'student') return;
    setEditForm({
      name: drawerUser.name || '',
      email: drawerUser.email || '',
      phone: drawerUser.phone || '',
      institute: drawerUser.institute || '',
      goal: drawerUser.goal || '',
      preferred_time_slot: drawerUser.preferred_time_slot || '',
      state: drawerUser.state || '',
      city: drawerUser.city || '',
      country: drawerUser.country || '',
      grade: drawerUser.grade || '',
      credits: drawerUser.credits || 0,
      bio: drawerUser.bio || ''
    });
    setEditingStudent(true);
  };

  const handleSaveStudentEdit = async () => {
    try {
      const res = await fetch(`${API}/admin/edit-student/${drawerUser.user_id}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Student profile updated!');
      setEditingStudent(false);
      setDrawerUser(null);
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handlePurgeSystem = async () => {
    if (!window.confirm('WARNING: This will delete ALL students, teachers, counsellors, classes, demos, assignments, and pricing. Only the Admin account will remain. This action is IRREVERSIBLE. Are you sure?')) return;
    if (!window.confirm('FINAL CONFIRMATION: Type "yes" to proceed. Everything will be deleted.')) return;
    try {
      const res = await fetch(`${API}/admin/purge-system`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('System purged! Fresh install state.');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  // ─── Computed ───

  const staff = useMemo(() => allUsers.filter(u =>
    (staffRoleFilter === 'all' || u.role === staffRoleFilter) &&
    u.role !== 'admin' &&
    (!staffSearch || u.name?.toLowerCase().includes(staffSearch.toLowerCase()) || u.email?.toLowerCase().includes(staffSearch.toLowerCase()) || (u.teacher_code || u.student_code || '').toLowerCase().includes(staffSearch.toLowerCase()))
  ), [allUsers, staffSearch, staffRoleFilter]);

  const teachers = useMemo(() => allUsers.filter(u => u.role === 'teacher'), [allUsers]);
  const pendingTeachers = useMemo(() => teachers.filter(t => !t.is_approved), [teachers]);

  const filteredClasses = useMemo(() => classes.filter(c =>
    (!classFilter.search || c.title?.toLowerCase().includes(classFilter.search.toLowerCase()) || c.teacher_name?.toLowerCase().includes(classFilter.search.toLowerCase())) &&
    (!classFilter.is_demo || (classFilter.is_demo === 'true' ? c.is_demo : !c.is_demo)) &&
    (!classFilter.status || c.status === classFilter.status)
  ), [classes, classFilter]);

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" /></div>;

  // ─── RENDER ───

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-9 h-9 text-sky-500" strokeWidth={2.5} />
              <div>
                <h1 className="text-xl font-bold text-slate-900">Operations Center</h1>
                <p className="text-xs text-slate-500">Kaimera Learning Admin</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button onClick={() => navigate('/demo-live-sheet')} size="sm" className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full text-xs font-bold" data-testid="admin-demo-live-sheet"><Zap className="w-3 h-3 mr-1" /> Demo Sheet</Button>
              <Button onClick={() => navigate('/history')} size="sm" variant="outline" className="rounded-full text-xs" data-testid="admin-history-link"><History className="w-3 h-3 mr-1" /> History</Button>
              <Button onClick={() => navigate('/learning-kit')} size="sm" variant="outline" className="rounded-full text-xs" data-testid="admin-learning-kit-link"><BookOpen className="w-3 h-3 mr-1" /> Learning Kit</Button>
              <span className="text-sm font-medium text-slate-700">{user?.name}</span>
              <Button onClick={handleLogout} variant="outline" size="sm" className="rounded-full" data-testid="logout-button"><LogOut className="w-3 h-3" /></Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Main Navigation */}
        <Tabs value={mainTab} onValueChange={setMainTab} className="w-full">
          <TabsList className="mb-6 bg-white border-2 border-slate-100 rounded-2xl p-1.5 shadow-sm">
            <TabsTrigger value="users" className="rounded-xl px-6 data-[state=active]:bg-sky-500 data-[state=active]:text-white" data-testid="users-tab"><Users className="w-4 h-4 mr-2" /> User Management</TabsTrigger>
            <TabsTrigger value="financials" className="rounded-xl px-6 data-[state=active]:bg-emerald-500 data-[state=active]:text-white" data-testid="financials-tab"><CreditCard className="w-4 h-4 mr-2" /> Financials</TabsTrigger>
            <TabsTrigger value="reports" className="rounded-xl px-6 data-[state=active]:bg-violet-500 data-[state=active]:text-white" data-testid="reports-tab"><BarChart3 className="w-4 h-4 mr-2" /> Reports</TabsTrigger>
          </TabsList>

          {/* ════════════════════════ USER MANAGEMENT ════════════════════════ */}
          <TabsContent value="users">
            <Tabs defaultValue="identity">
              <TabsList className="mb-4">
                <TabsTrigger value="identity" data-testid="identity-creator-tab">Identity Creator</TabsTrigger>
                <TabsTrigger value="directory" data-testid="directory-tab">Staff & Student Directory</TabsTrigger>
                <TabsTrigger value="credentials" data-testid="credentials-sub-tab">Credentials & Access</TabsTrigger>
              </TabsList>

              {/* ── Identity Creator ── */}
              <TabsContent value="identity">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Creation Form */}
                  <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                    <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2"><UserPlus className="w-5 h-5 text-sky-500" /> Identity Creator</h3>

                    {credsResult ? (
                      <div className="space-y-4">
                        <div className="bg-emerald-50 rounded-2xl p-6 border-2 border-emerald-200">
                          <h4 className="text-lg font-bold text-emerald-800 mb-3">Account Created!</h4>
                          <div className="bg-white rounded-xl p-4 font-mono text-sm space-y-1">
                            <p><strong>Email:</strong> {credsResult.email}</p>
                            <p><strong>Password:</strong> {credsResult.password}</p>
                            {credsResult.code && <p><strong>ID:</strong> {credsResult.code}</p>}
                          </div>
                          <div className="flex gap-2 mt-4">
                            <Button onClick={() => { navigator.clipboard.writeText(`Email: ${credsResult.email}\nPassword: ${credsResult.password}${credsResult.code ? `\nID: ${credsResult.code}` : ''}`); toast.success('Copied!'); }} className="bg-emerald-500 text-white rounded-full" data-testid="copy-creds-btn"><Copy className="w-4 h-4 mr-1" /> Copy</Button>
                            <Button onClick={() => setCredsResult(null)} variant="outline" className="rounded-full">Create Another</Button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <form onSubmit={handleCreateUser} className="space-y-4">
                        {/* Role Selector */}
                        <div>
                          <Label>Role</Label>
                          <div className="grid grid-cols-3 gap-2 mt-1">
                            {['student', 'teacher', 'counsellor'].map(r => (
                              <button key={r} type="button" onClick={() => setCreateRole(r)}
                                className={`py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${createRole === r ? (r === 'student' ? 'bg-sky-500 text-white border-sky-500' : r === 'teacher' ? 'bg-amber-500 text-white border-amber-500' : 'bg-violet-500 text-white border-violet-500') : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}
                                data-testid={`role-btn-${r}`}
                              >{r.charAt(0).toUpperCase() + r.slice(1)}</button>
                            ))}
                          </div>
                        </div>
                        {/* Common Fields */}
                        <div className="grid grid-cols-2 gap-3">
                          <div><Label>Name *</Label><Input value={createForm.name} onChange={e => setCreateForm({...createForm, name: e.target.value})} className="rounded-xl" required data-testid="create-name" /></div>
                          <div><Label>Email *</Label><Input type="email" value={createForm.email} onChange={e => setCreateForm({...createForm, email: e.target.value})} className="rounded-xl" required data-testid="create-email" /></div>
                          <div><Label>Password *</Label><Input value={createForm.password} onChange={e => setCreateForm({...createForm, password: e.target.value})} className="rounded-xl" required data-testid="create-password" /></div>
                          <div><Label>Phone</Label><Input value={createForm.phone} onChange={e => setCreateForm({...createForm, phone: e.target.value})} className="rounded-xl" data-testid="create-phone" /></div>
                        </div>
                        {/* Student-specific Fields */}
                        {createRole === 'student' && (
                          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                            <div><Label>Grade/Class</Label>
                              <select value={createForm.grade} onChange={e => setCreateForm({...createForm, grade: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 bg-white h-10 text-sm" data-testid="create-grade">
                                <option value="">Select...</option>
                                {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>)}
                              </select>
                            </div>
                            <div><Label>Institute</Label><Input value={createForm.institute} onChange={e => setCreateForm({...createForm, institute: e.target.value})} className="rounded-xl" data-testid="create-institute" /></div>
                            <div><Label>State</Label><Input value={createForm.state} onChange={e => setCreateForm({...createForm, state: e.target.value})} className="rounded-xl" data-testid="create-state" /></div>
                            <div><Label>City</Label><Input value={createForm.city} onChange={e => setCreateForm({...createForm, city: e.target.value})} className="rounded-xl" data-testid="create-city" /></div>
                            <div><Label>Country</Label><Input value={createForm.country} onChange={e => setCreateForm({...createForm, country: e.target.value})} className="rounded-xl" data-testid="create-country" /></div>
                            <div><Label>Goal</Label><Input value={createForm.goal} onChange={e => setCreateForm({...createForm, goal: e.target.value})} className="rounded-xl" data-testid="create-goal" /></div>
                            <div className="col-span-2">
                              <Label>Preferred Time</Label>
                              <div className="grid grid-cols-2 gap-2">
                                <Input type="datetime-local" value={createForm.preferred_time_slot?.split(' to ')[0] || ''} onChange={e => {
                                  const end = createForm.preferred_time_slot?.split(' to ')[1] || '';
                                  setCreateForm({...createForm, preferred_time_slot: `${e.target.value}${end ? ` to ${end}` : ''}`});
                                }} className="rounded-xl text-sm" data-testid="create-time-from" />
                                <Input type="datetime-local" value={createForm.preferred_time_slot?.split(' to ')[1] || ''} onChange={e => {
                                  const start = createForm.preferred_time_slot?.split(' to ')[0] || '';
                                  setCreateForm({...createForm, preferred_time_slot: `${start} to ${e.target.value}`});
                                }} className="rounded-xl text-sm" data-testid="create-time-to" />
                              </div>
                            </div>
                          </div>
                        )}
                        <Button type="submit" className={`w-full rounded-full py-6 font-bold text-white ${createRole === 'student' ? 'bg-sky-500 hover:bg-sky-600' : createRole === 'teacher' ? 'bg-amber-500 hover:bg-amber-600' : 'bg-violet-500 hover:bg-violet-600'}`} data-testid="create-user-submit">
                          <UserPlus className="w-5 h-5 mr-2" /> Create {createRole.charAt(0).toUpperCase() + createRole.slice(1)}
                        </Button>
                      </form>
                    )}
                  </div>

                  {/* Pending Teacher Approvals */}
                  <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                    <h3 className="text-lg font-bold text-slate-900 mb-4">Pending Approvals ({pendingTeachers.length})</h3>
                    {pendingTeachers.length === 0 ? (
                      <p className="text-slate-500 text-sm py-8 text-center">No pending approvals</p>
                    ) : (
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {pendingTeachers.map(t => (
                          <div key={t.user_id} className="flex items-center justify-between p-3 bg-amber-50 rounded-xl border border-amber-200">
                            <div>
                              <p className="font-semibold text-slate-900 text-sm">{t.name}</p>
                              <p className="text-xs text-slate-500">{t.email}</p>
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => handleApproveTeacher(t.user_id, true)} size="sm" className="bg-emerald-500 text-white rounded-full" data-testid={`approve-${t.user_id}`}><Check className="w-3 h-3" /></Button>
                              <Button onClick={() => handleApproveTeacher(t.user_id, false)} size="sm" variant="outline" className="rounded-full border-red-200 text-red-600" data-testid={`reject-${t.user_id}`}><X className="w-3 h-3" /></Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* ── Staff & Student Directory ── */}
              <TabsContent value="directory">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                  {/* Search + Filters */}
                  <div className="flex flex-wrap gap-3 mb-4 items-end">
                    <div className="flex-1 min-w-[250px]">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input value={staffSearch} onChange={e => setStaffSearch(e.target.value)} placeholder="Search by name, email, or ID..." className="pl-10 rounded-xl" data-testid="directory-search" />
                      </div>
                    </div>
                    <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
                      {['all', 'student', 'teacher', 'counsellor'].map(r => (
                        <button key={r} onClick={() => setStaffRoleFilter(r)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${staffRoleFilter === r ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`} data-testid={`filter-${r}`}>{r === 'all' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}s</button>
                      ))}
                    </div>
                  </div>

                  {/* Data Table */}
                  <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Name</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Role</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">ID</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Email</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Credits</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Status</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {staff.slice(0, 50).map(u => (
                          <tr key={u.user_id} className="border-t border-slate-100 hover:bg-slate-50 transition-colors" data-testid={`dir-row-${u.user_id}`}>
                            <td className="px-4 py-3">
                              <button onClick={() => handleOpenDrawer(u.user_id)} className="flex items-center gap-2 text-left hover:text-sky-600 transition-colors" data-testid={`open-drawer-${u.user_id}`}>
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold ${u.role === 'teacher' ? 'bg-amber-500' : u.role === 'student' ? 'bg-sky-500' : 'bg-violet-500'}`}>{u.name?.charAt(0)}</div>
                                <span className="font-medium text-sm">{u.name}</span>
                              </button>
                            </td>
                            <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                            <td className="px-4 py-3 font-mono text-xs text-slate-500">{u.teacher_code || u.student_code || '-'}</td>
                            <td className="px-4 py-3 text-sm text-slate-600">{u.email}</td>
                            <td className="px-4 py-3 text-sm font-medium text-slate-900">{u.credits || 0}</td>
                            <td className="px-4 py-3">
                              {u.is_blocked ? <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-semibold">Blocked</span>
                                : u.is_approved === false ? <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-xs font-semibold">Pending</span>
                                : <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-semibold">Active</span>}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end gap-1">
                                <Button onClick={() => { setCreditUser(u.user_id); setCreditsDialog(true); }} variant="ghost" size="sm" className="h-7 px-2 text-slate-500" data-testid={`credits-${u.user_id}`}><DollarSign className="w-3.5 h-3.5" /></Button>
                                <Button onClick={() => handleBlock(u.user_id, !u.is_blocked)} variant="ghost" size="sm" className={`h-7 px-2 ${u.is_blocked ? 'text-emerald-500' : 'text-amber-500'}`} data-testid={`block-${u.user_id}`}><Ban className="w-3.5 h-3.5" /></Button>
                                <Button onClick={() => handleDelete(u.user_id)} variant="ghost" size="sm" className="h-7 px-2 text-red-500" data-testid={`delete-${u.user_id}`}><Trash2 className="w-3.5 h-3.5" /></Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {staff.length > 50 && <p className="text-xs text-slate-400 text-center py-3">Showing 50 of {staff.length}</p>}
                  </div>
                </div>
              </TabsContent>

              {/* ── Credentials & Access ── */}
              <TabsContent value="credentials">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                    <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><KeyRound className="w-5 h-5 text-amber-500" /> Reset Password</h3>
                    <div className="space-y-3">
                      <div><Label>User Email</Label><Input value={resetEmail} onChange={e => setResetEmail(e.target.value)} placeholder="user@example.com" className="rounded-xl" data-testid="reset-email-input" /></div>
                      <div><Label>New Password</Label><Input value={resetPassword} onChange={e => setResetPassword(e.target.value)} placeholder="New password" className="rounded-xl" data-testid="reset-password-input" /></div>
                      <Button onClick={handleResetPassword} className="bg-amber-500 hover:bg-amber-600 text-white rounded-full w-full" data-testid="reset-password-btn"><KeyRound className="w-4 h-4 mr-2" /> Reset</Button>
                    </div>
                  </div>
                  <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                    <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><Award className="w-5 h-5 text-violet-500" /> Badge Management</h3>
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-2">
                        <Input value={newTemplateName} onChange={e => setNewTemplateName(e.target.value)} placeholder="Badge name" className="rounded-xl" data-testid="template-name-input" />
                        <Button onClick={handleCreateBadgeTemplate} className="bg-violet-500 text-white rounded-xl" data-testid="create-template-btn"><Plus className="w-4 h-4 mr-1" /> Template</Button>
                      </div>
                      {badgeTemplates.length > 0 && <div className="flex flex-wrap gap-1">{badgeTemplates.map(t => (
                        <span key={t.badge_id} className="bg-violet-50 text-violet-700 px-2 py-1 rounded-lg text-xs flex items-center gap-1">{t.name} <button onClick={() => handleDeleteBadgeTemplate(t.badge_id)} className="text-red-400 hover:text-red-600"><X className="w-3 h-3" /></button></span>
                      ))}</div>}
                      <div className="border-t border-slate-100 pt-3 space-y-2">
                        <select value={badgeTarget} onChange={e => setBadgeTarget(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="badge-user-select">
                          <option value="">Select user...</option>
                          {allUsers.filter(u => u.role !== 'admin').map(u => <option key={u.user_id} value={u.user_id}>{u.name} ({u.role})</option>)}
                        </select>
                        <select value={selectedTemplateBadge} onChange={e => { setSelectedTemplateBadge(e.target.value); setBadgeName(''); }} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="badge-template-select">
                          <option value="">Choose template...</option>
                          {badgeTemplates.map(t => <option key={t.badge_id} value={t.name}>{t.name}</option>)}
                        </select>
                        <Button onClick={handleAssignBadge} className="bg-violet-500 text-white rounded-full w-full" data-testid="assign-badge-btn"><Award className="w-4 h-4 mr-1" /> Assign</Button>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ════════════════════════ FINANCIALS ════════════════════════ */}
          <TabsContent value="financials">
            <Tabs defaultValue="ledger">
              <TabsList className="mb-4">
                <TabsTrigger value="ledger" data-testid="ledger-tab">Transaction Ledger</TabsTrigger>
                <TabsTrigger value="proofs" data-testid="proofs-tab">Proofs & Approvals ({pendingProofs.length})</TabsTrigger>
                <TabsTrigger value="pricing" data-testid="pricing-tab" onClick={() => { if (!pricingLoaded) fetchPricing(); }}><Settings className="w-3.5 h-3.5 mr-1.5" /> System Pricing</TabsTrigger>
              </TabsList>

              {/* ── Transaction Ledger ── */}
              <TabsContent value="ledger">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                  {/* Filters */}
                  <div className="flex flex-wrap gap-3 mb-4 items-end">
                    <div className="flex-1 min-w-[200px]">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input value={txnSearch} onChange={e => setTxnSearch(e.target.value)} placeholder="Search by name, email, ID..." className="pl-10 rounded-xl" data-testid="txn-search" />
                      </div>
                    </div>
                    <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
                      {['all', 'student', 'teacher', 'counsellor'].map(r => (
                        <button key={r} onClick={() => setTxnRoleFilter(r)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${txnRoleFilter === r ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`} data-testid={`txn-filter-${r}`}>{r === 'all' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}</button>
                      ))}
                    </div>
                    <Input type="date" value={txnDateFrom} onChange={e => setTxnDateFrom(e.target.value)} className="rounded-xl w-36" data-testid="txn-date-from" />
                    <Input type="date" value={txnDateTo} onChange={e => setTxnDateTo(e.target.value)} className="rounded-xl w-36" data-testid="txn-date-to" />
                    <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
                      <button onClick={() => setTxnView('daily')} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${txnView === 'daily' ? 'bg-white shadow-sm' : 'text-slate-500'}`} data-testid="txn-view-daily">Daily</button>
                      <button onClick={() => setTxnView('detail')} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${txnView === 'detail' ? 'bg-white shadow-sm' : 'text-slate-500'}`} data-testid="txn-view-detail">Detail</button>
                    </div>
                    <Button onClick={handleFilterTransactions} className="bg-sky-500 text-white rounded-xl" data-testid="txn-apply-filter"><Filter className="w-4 h-4 mr-1" /> Apply</Button>
                  </div>

                  {/* Daily Revenue View */}
                  {txnView === 'daily' ? (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Date</th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600">Transactions</th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-emerald-600">Credits Added</th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-red-600">Deductions</th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-900">Net</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dailyRevenue.map((d, i) => (
                            <tr key={i} className="border-t border-slate-100" data-testid={`daily-row-${i}`}>
                              <td className="px-4 py-3 text-sm font-medium text-slate-900">{d.date}</td>
                              <td className="px-4 py-3 text-sm text-right text-slate-600">{d.count}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold text-emerald-600">+{d.total_credits_added?.toFixed(1)}</td>
                              <td className="px-4 py-3 text-sm text-right font-semibold text-red-600">-{d.total_deductions?.toFixed(1)}</td>
                              <td className={`px-4 py-3 text-sm text-right font-bold ${d.total_revenue >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>{d.total_revenue >= 0 ? '+' : ''}{d.total_revenue?.toFixed(1)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {dailyRevenue.length === 0 && <p className="text-sm text-slate-400 text-center py-8">No transactions found</p>}
                    </div>
                  ) : (
                    /* Detailed Transaction View */
                    <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                      <table className="w-full">
                        <thead className="bg-slate-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">User</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Role</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Type</th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600">Amount</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Description</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {transactions.slice(0, 100).map((txn, i) => (
                            <tr key={txn.transaction_id || i} className="border-t border-slate-100 hover:bg-slate-50" data-testid={`txn-row-${i}`}>
                              <td className="px-4 py-3">
                                <button onClick={() => txn.user_id && handleOpenDrawer(txn.user_id)} className="text-sm font-medium text-slate-900 hover:text-sky-600">{txn.user_name || 'Unknown'}</button>
                                <p className="text-xs text-slate-400 font-mono">{txn.user_code}</p>
                              </td>
                              <td className="px-4 py-3"><RoleBadge role={txn.user_role} /></td>
                              <td className="px-4 py-3 text-xs text-slate-500">{txn.type}</td>
                              <td className={`px-4 py-3 text-sm text-right font-bold ${txn.amount > 0 ? 'text-emerald-600' : 'text-red-600'}`}>{txn.amount > 0 ? '+' : ''}{txn.amount}</td>
                              <td className="px-4 py-3 text-sm text-slate-600 max-w-[200px] truncate">{txn.description}</td>
                              <td className="px-4 py-3 text-xs text-slate-400">{txn.created_at?.slice(0, 10)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* ── Proofs & Approvals ── */}
              <TabsContent value="proofs">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                  <div className="flex flex-wrap gap-3 items-end mb-4">
                    <div><Label className="text-xs text-slate-500">From</Label><Input type="date" value={proofDateFrom} onChange={e => setProofDateFrom(e.target.value)} className="rounded-xl w-40" data-testid="proof-date-from" /></div>
                    <div><Label className="text-xs text-slate-500">To</Label><Input type="date" value={proofDateTo} onChange={e => setProofDateTo(e.target.value)} className="rounded-xl w-40" data-testid="proof-date-to" /></div>
                    <Button onClick={async () => {
                      const params = new URLSearchParams();
                      if (proofDateFrom) params.set('date_from', proofDateFrom);
                      if (proofDateTo) params.set('date_to', proofDateTo);
                      const res = await fetch(`${API}/admin/approved-proofs?${params}`, { credentials: 'include' });
                      if (res.ok) setPendingProofs(await res.json());
                    }} className="bg-sky-500 text-white rounded-xl" data-testid="filter-proofs-btn"><Filter className="w-4 h-4 mr-1" /> Filter</Button>
                  </div>
                  {pendingProofs.length === 0 ? (
                    <div className="text-center py-12"><Shield className="w-12 h-12 text-slate-300 mx-auto mb-3" /><p className="text-slate-500">No pending proofs</p></div>
                  ) : (
                    <div className="space-y-3">
                      {pendingProofs.map(proof => (
                        <div key={proof.proof_id} className="rounded-2xl border border-slate-200 p-4" data-testid={`proof-${proof.proof_id}`}>
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h4 className="font-bold text-slate-900 text-sm">{proof.class_title || proof.class_details?.title || 'Class'}</h4>
                              <p className="text-xs text-slate-500">
                                {proof.teacher_details && `Teacher: ${proof.teacher_details.name}`}
                                {proof.student_details && ` | Student: ${proof.student_details.name}`}
                              </p>
                            </div>
                            <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs font-semibold">Awaiting</span>
                          </div>
                          {proof.description && <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-2 mb-2">{proof.description}</p>}
                          <div className="flex gap-2">
                            <Button onClick={() => handleApproveProof(proof.proof_id, true)} size="sm" className="bg-emerald-500 text-white rounded-full flex-1" data-testid={`approve-proof-${proof.proof_id}`}><Check className="w-3 h-3 mr-1" /> Approve & Credit</Button>
                            <Button onClick={() => handleApproveProof(proof.proof_id, false)} size="sm" variant="outline" className="rounded-full border-red-200 text-red-600 flex-1" data-testid={`reject-proof-${proof.proof_id}`}><X className="w-3 h-3 mr-1" /> Reject</Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* ── System Pricing ── */}
              <TabsContent value="pricing">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 max-w-2xl">
                  <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2"><Settings className="w-5 h-5 text-sky-500" /> Unified Rates Dashboard</h3>
                  <p className="text-sm text-slate-500 mb-6">Set global pricing for all student-teacher transactions. These rates apply to all new assignments.</p>
                  <div className="space-y-6">
                    <div className="bg-sky-50 rounded-2xl p-5 border border-sky-200">
                      <h4 className="text-sm font-bold text-sky-800 mb-3">Student Rates (Deducted from wallet)</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs text-sky-700">Demo Class Rate (credits)</Label>
                          <Input type="number" step="0.1" min="0" value={pricingForm.demo_price_student} onChange={e => setPricingForm({...pricingForm, demo_price_student: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-demo-student" />
                        </div>
                        <div>
                          <Label className="text-xs text-sky-700">Regular Class Fee (credits)</Label>
                          <Input type="number" step="0.1" min="0" value={pricingForm.class_price_student} onChange={e => setPricingForm({...pricingForm, class_price_student: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-class-student" />
                        </div>
                      </div>
                    </div>
                    <div className="bg-amber-50 rounded-2xl p-5 border border-amber-200">
                      <h4 className="text-sm font-bold text-amber-800 mb-3">Teacher Rates (Credited to wallet)</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs text-amber-700">Demo Session Credit (credits)</Label>
                          <Input type="number" step="0.1" min="0" value={pricingForm.demo_earning_teacher} onChange={e => setPricingForm({...pricingForm, demo_earning_teacher: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-demo-teacher" />
                        </div>
                        <div>
                          <Label className="text-xs text-amber-700">Regular Class Pay (credits)</Label>
                          <Input type="number" step="0.1" min="0" value={pricingForm.class_earning_teacher} onChange={e => setPricingForm({...pricingForm, class_earning_teacher: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-class-teacher" />
                        </div>
                      </div>
                    </div>
                    <Button onClick={handleSavePricing} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="save-pricing-btn">
                      <Save className="w-5 h-5 mr-2" /> Save System Pricing
                    </Button>
                  </div>
                  {/* System Reset */}
                  <div className="mt-8 bg-red-50 rounded-2xl p-5 border border-red-200">
                    <h4 className="text-sm font-bold text-red-800 mb-2">Danger Zone</h4>
                    <p className="text-xs text-red-600 mb-3">Purge all system data (students, teachers, counsellors, classes, demos, pricing). Only Admin account will remain. This is irreversible.</p>
                    <Button onClick={handlePurgeSystem} variant="outline" className="border-red-300 text-red-600 hover:bg-red-100 rounded-full" data-testid="purge-system-btn">
                      <Trash2 className="w-4 h-4 mr-2" /> Purge System (Fresh Install)
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ════════════════════════ REPORTS ════════════════════════ */}
          <TabsContent value="reports">
            <Tabs defaultValue="counsellors">
              <TabsList className="mb-4">
                <TabsTrigger value="counsellors" data-testid="counsellors-report-tab">Counsellor Tracking</TabsTrigger>
                <TabsTrigger value="classes" data-testid="classes-report-tab">Class Overview</TabsTrigger>
                <TabsTrigger value="complaints" data-testid="complaints-report-tab">Complaints ({complaints.length})</TabsTrigger>
              </TabsList>

              {/* ── Counsellor Tracking ── */}
              <TabsContent value="counsellors">
                {counsellorTracking.length === 0 ? (
                  <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center"><p className="text-slate-500">No counsellors found</p></div>
                ) : (
                  <div className="space-y-4">
                    {counsellorTracking.map(c => (
                      <div key={c.user_id} className="bg-white rounded-2xl border-2 border-slate-200 overflow-hidden" data-testid={`counsellor-track-${c.user_id}`}>
                        <div className="p-5">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3 cursor-pointer" onClick={() => handleOpenDrawer(c.user_id)}>
                              <div className="w-12 h-12 bg-gradient-to-br from-violet-400 to-violet-500 rounded-xl flex items-center justify-center text-white font-bold">{c.name?.charAt(0)}</div>
                              <div>
                                <h3 className="font-bold text-slate-900 hover:text-sky-600 transition-colors">{c.name}</h3>
                                <p className="text-xs text-slate-500">{c.email}{c.phone ? ` | ${c.phone}` : ''}</p>
                              </div>
                            </div>
                            <Button onClick={() => fetchCounsellorDailyStats(c.user_id)} variant="outline" size="sm" className="rounded-full" data-testid={`toggle-chart-${c.user_id}`}>
                              {expandedCounsellor === c.user_id ? 'Hide' : 'Daily Stats'}
                            </Button>
                          </div>
                          <div className="grid grid-cols-4 gap-2">
                            <div className="bg-slate-50 rounded-lg p-2 text-center"><p className="text-[10px] text-slate-500">Total</p><p className="text-lg font-bold text-slate-900">{c.total_assignments}</p></div>
                            <div className="bg-emerald-50 rounded-lg p-2 text-center"><p className="text-[10px] text-emerald-600">Active</p><p className="text-lg font-bold text-emerald-700">{c.active_assignments}</p></div>
                            <div className="bg-amber-50 rounded-lg p-2 text-center"><p className="text-[10px] text-amber-600">Pending</p><p className="text-lg font-bold text-amber-700">{c.pending_assignments}</p></div>
                            <div className="bg-red-50 rounded-lg p-2 text-center"><p className="text-[10px] text-red-600">Rejected</p><p className="text-lg font-bold text-red-700">{c.rejected_assignments}</p></div>
                          </div>
                        </div>
                        {expandedCounsellor === c.user_id && (
                          <div className="border-t border-slate-100 p-5 bg-slate-50">
                            <h4 className="text-xs font-semibold text-slate-600 mb-2">Daily Activity</h4>
                            {counsellorDailyStats[c.user_id]?.length > 0 ? (
                              <ResponsiveContainer width="100%" height={240}>
                                <BarChart data={counsellorDailyStats[c.user_id]}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                                  <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '12px' }} />
                                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                                  <Bar dataKey="leads" name="Leads" fill="#38bdf8" radius={[3, 3, 0, 0]} />
                                  <Bar dataKey="allotments" name="Allotments" fill="#a78bfa" radius={[3, 3, 0, 0]} />
                                  <Bar dataKey="sessions" name="Sessions" fill="#34d399" radius={[3, 3, 0, 0]} />
                                </BarChart>
                              </ResponsiveContainer>
                            ) : <p className="text-sm text-slate-400 text-center py-6">No daily data yet</p>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>

              {/* ── Class Overview ── */}
              <TabsContent value="classes">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                  <div className="flex flex-wrap gap-3 mb-4 items-end">
                    <div className="flex-1"><Input placeholder="Search class, teacher..." value={classFilter.search} onChange={e => setClassFilter({...classFilter, search: e.target.value})} className="rounded-xl" data-testid="class-search" /></div>
                    <select value={classFilter.is_demo} onChange={e => setClassFilter({...classFilter, is_demo: e.target.value})} className="rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10" data-testid="class-type-filter">
                      <option value="">All</option><option value="true">Demo</option><option value="false">Regular</option>
                    </select>
                    <select value={classFilter.status} onChange={e => setClassFilter({...classFilter, status: e.target.value})} className="rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10" data-testid="class-status-filter">
                      <option value="">All Status</option><option value="scheduled">Scheduled</option><option value="in_progress">In Progress</option><option value="completed">Completed</option>
                    </select>
                  </div>
                  <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Title</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Teacher</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Date</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Type</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Status</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Students</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredClasses.map(cls => (
                          <tr key={cls.class_id} className="border-t border-slate-100" data-testid={`class-row-${cls.class_id}`}>
                            <td className="px-3 py-2 text-sm font-medium text-slate-900">{cls.title}</td>
                            <td className="px-3 py-2 text-sm text-slate-600">{cls.teacher_name}</td>
                            <td className="px-3 py-2 text-xs text-slate-500">{cls.date}</td>
                            <td className="px-3 py-2">{cls.is_demo ? <span className="bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-xs">Demo</span> : <span className="bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full text-xs">Regular</span>}</td>
                            <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls.status === 'scheduled' ? 'bg-sky-100 text-sky-700' : cls.status === 'in_progress' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{cls.status}</span></td>
                            <td className="px-3 py-2 text-xs text-slate-500">{cls.enrolled_students?.length || 0}/{cls.max_students}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </TabsContent>

              {/* ── Complaints ── */}
              <TabsContent value="complaints">
                {complaints.length === 0 ? (
                  <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center"><p className="text-slate-500">No complaints</p></div>
                ) : (
                  <div className="space-y-3">
                    {complaints.map(c => (
                      <div key={c.complaint_id} className="bg-white rounded-2xl border-2 border-slate-200 p-5" data-testid={`complaint-${c.complaint_id}`}>
                        <div className="flex items-start justify-between mb-2">
                          <div><h4 className="font-bold text-slate-900 text-sm">{c.subject}</h4><p className="text-xs text-slate-500">By: {c.raised_by_name} ({c.raised_by_role})</p></div>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${c.status === 'open' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>{c.status}</span>
                        </div>
                        <p className="text-sm text-slate-600">{c.description}</p>
                      </div>
                    ))}
                  </div>
                )}
                <Button onClick={() => navigate('/complaints')} className="mt-4 bg-sky-500 text-white rounded-full"><MessageSquare className="w-4 h-4 mr-2" /> Manage</Button>
              </TabsContent>
            </Tabs>
          </TabsContent>
        </Tabs>
      </div>

      {/* ═══════ DRAWER: User Drill-Down ═══════ */}
      <Dialog open={!!drawerUser} onOpenChange={(open) => { if (!open) { setDrawerUser(null); setEditingStudent(false); } }}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-xl font-bold text-slate-900">User Profile</DialogTitle></DialogHeader>
          {drawerUser && (
            <div className="space-y-4 mt-2">
              <div className={`rounded-2xl p-5 text-white ${drawerUser.role === 'teacher' ? 'bg-gradient-to-br from-amber-400 to-amber-500' : drawerUser.role === 'student' ? 'bg-gradient-to-br from-sky-400 to-sky-500' : 'bg-gradient-to-br from-violet-400 to-violet-500'}`}>
                <h3 className="text-xl font-bold" data-testid="drawer-name">{drawerUser.name}</h3>
                <p className="text-white/80">{drawerUser.email}</p>
                <div className="flex flex-wrap gap-2 mt-2 text-xs">
                  <span className="bg-white/20 px-2 py-1 rounded-full">{drawerUser.role}</span>
                  {drawerUser.teacher_code && <span className="bg-white/20 px-2 py-1 rounded-full font-mono">{drawerUser.teacher_code}</span>}
                  {drawerUser.student_code && <span className="bg-white/20 px-2 py-1 rounded-full font-mono">{drawerUser.student_code}</span>}
                  {drawerUser.is_blocked && <span className="bg-red-500/80 px-2 py-1 rounded-full font-bold">BLOCKED</span>}
                </div>
              </div>

              {/* Student Edit Mode */}
              {editingStudent && drawerUser.role === 'student' ? (
                <div className="space-y-3 bg-sky-50 rounded-2xl p-4 border border-sky-200">
                  <h4 className="text-sm font-bold text-sky-800 flex items-center gap-1.5"><Pencil className="w-3.5 h-3.5" /> Edit Student Profile</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label className="text-xs">Name</Label><Input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-name" /></div>
                    <div><Label className="text-xs">Email</Label><Input value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-email" /></div>
                    <div><Label className="text-xs">Phone</Label><Input value={editForm.phone} onChange={e => setEditForm({...editForm, phone: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-phone" /></div>
                    <div><Label className="text-xs">Credits</Label><Input type="number" step="0.1" value={editForm.credits} onChange={e => setEditForm({...editForm, credits: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-credits" /></div>
                    <div><Label className="text-xs">Grade</Label>
                      <select value={editForm.grade} onChange={e => setEditForm({...editForm, grade: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 bg-white text-sm h-10" data-testid="edit-student-grade">
                        <option value="">Select...</option>
                        {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>)}
                      </select>
                    </div>
                    <div><Label className="text-xs">Institute</Label><Input value={editForm.institute} onChange={e => setEditForm({...editForm, institute: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-institute" /></div>
                    <div><Label className="text-xs">Goal</Label><Input value={editForm.goal} onChange={e => setEditForm({...editForm, goal: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-goal" /></div>
                    <div><Label className="text-xs">Preferred Time</Label><Input value={editForm.preferred_time_slot} onChange={e => setEditForm({...editForm, preferred_time_slot: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-time" /></div>
                    <div><Label className="text-xs">State</Label><Input value={editForm.state} onChange={e => setEditForm({...editForm, state: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-state" /></div>
                    <div><Label className="text-xs">City</Label><Input value={editForm.city} onChange={e => setEditForm({...editForm, city: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-city" /></div>
                    <div><Label className="text-xs">Country</Label><Input value={editForm.country} onChange={e => setEditForm({...editForm, country: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-country" /></div>
                    <div><Label className="text-xs">Bio</Label><Input value={editForm.bio} onChange={e => setEditForm({...editForm, bio: e.target.value})} className="rounded-xl bg-white text-sm" data-testid="edit-student-bio" /></div>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button onClick={handleSaveStudentEdit} className="flex-1 bg-sky-500 hover:bg-sky-600 text-white rounded-full font-bold" data-testid="save-student-edit-btn"><Save className="w-4 h-4 mr-1" /> Save Changes</Button>
                    <Button onClick={() => setEditingStudent(false)} variant="outline" className="rounded-full">Cancel</Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">Credits</p><p className="text-lg font-bold">{drawerUser.credits || 0}</p></div>
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">Phone</p><p className="text-xs font-medium">{drawerUser.phone || 'N/A'}</p></div>
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">Grade</p><p className="text-xs font-medium">{drawerUser.grade ? `Class ${drawerUser.grade}` : 'N/A'}</p></div>
                  </div>
                  {/* Admin Actions */}
                  {drawerUser.role !== 'admin' && (
                    <div className="flex gap-2 flex-wrap">
                      {drawerUser.role === 'student' && (
                        <Button onClick={handleStartEditStudent} variant="outline" className="flex-1 rounded-full text-xs border-sky-200 text-sky-600" data-testid="drawer-edit-student-btn"><Pencil className="w-3 h-3 mr-1" /> Edit Profile</Button>
                      )}
                      <Button onClick={() => { setCreditUser(drawerUser.user_id); setCreditsDialog(true); }} variant="outline" className="flex-1 rounded-full text-xs"><DollarSign className="w-3 h-3 mr-1" /> Credits</Button>
                      <Button onClick={() => handleBlock(drawerUser.user_id, !drawerUser.is_blocked)} variant="outline" className={`flex-1 rounded-full text-xs ${drawerUser.is_blocked ? 'border-emerald-200 text-emerald-600' : 'border-amber-200 text-amber-600'}`} data-testid="drawer-block-btn"><Ban className="w-3 h-3 mr-1" /> {drawerUser.is_blocked ? 'Unblock' : 'Block'}</Button>
                      <Button onClick={() => handleDelete(drawerUser.user_id)} variant="outline" className="flex-1 rounded-full text-xs border-red-200 text-red-600" data-testid="drawer-delete-btn"><Trash2 className="w-3 h-3 mr-1" /> Delete</Button>
                    </div>
                  )}
                </>
              )}
              {/* Drill-down data */}
              {drawerData && (
                <>
                  {drawerData.assignments?.length > 0 && (
                    <div><p className="text-xs font-semibold text-slate-700 mb-1">Assignments ({drawerData.assignments.length})</p>
                      <div className="space-y-1 max-h-28 overflow-y-auto">{drawerData.assignments.map((a, i) => (
                        <div key={i} className="bg-slate-50 rounded-lg p-2 flex justify-between text-xs">
                          <span>{a.student_name || a.teacher_name || '-'}</span>
                          <span className={`font-semibold ${a.status === 'approved' ? 'text-emerald-600' : a.status === 'pending' ? 'text-amber-600' : 'text-red-600'}`}>{a.status}</span>
                        </div>
                      ))}</div>
                    </div>
                  )}
                  {drawerData.classes?.length > 0 && (
                    <div><p className="text-xs font-semibold text-slate-700 mb-1">Classes ({drawerData.classes.length})</p>
                      <div className="space-y-1 max-h-28 overflow-y-auto">{drawerData.classes.map((c, i) => (
                        <div key={i} className="bg-slate-50 rounded-lg p-2 flex justify-between text-xs">
                          <span>{c.title} ({c.subject})</span>
                          <span className="text-slate-500">{c.date}</span>
                        </div>
                      ))}</div>
                    </div>
                  )}
                  {drawerData.transactions?.length > 0 && (
                    <div><p className="text-xs font-semibold text-slate-700 mb-1">Wallet History ({drawerData.transactions.length})</p>
                      <div className="space-y-1 max-h-28 overflow-y-auto">{drawerData.transactions.map((t, i) => (
                        <div key={i} className="bg-slate-50 rounded-lg p-2 flex justify-between text-xs">
                          <span>{t.description}</span>
                          <span className={`font-semibold ${t.amount > 0 ? 'text-emerald-600' : 'text-red-600'}`}>{t.amount > 0 ? '+' : ''}{t.amount}</span>
                        </div>
                      ))}</div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ═══════ Credits Dialog ═══════ */}
      <Dialog open={creditsDialog} onOpenChange={setCreditsDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle>Adjust Credits</DialogTitle></DialogHeader>
          <form onSubmit={handleAdjustCredits} className="space-y-4 mt-4">
            <select value={creditAction} onChange={e => setCreditAction(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="credit-action-select">
              <option value="add">Add Credits</option><option value="deduct">Deduct Credits</option>
            </select>
            <Input type="number" step="0.1" value={creditAmount} onChange={e => setCreditAmount(e.target.value)} placeholder="Amount" className="rounded-xl" required data-testid="credit-amount-input" />
            <Button type="submit" className="w-full bg-sky-500 text-white rounded-full py-6 font-bold" data-testid="submit-credits">Adjust</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
