import { Country, State, City } from "country-state-city";
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
  Ban, ChevronDown, ChevronUp, Calendar, CreditCard, BarChart3, Play, Settings, Save, Pencil, IndianRupee, Download,
  Mail, CheckCircle
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getApiError, API , apiFetch} from '../utils/api';
import { useDateRangeFilter } from '../components/DateRangeFilter';
import EmailTemplateManager from '../components/EmailTemplateManager';
import SystemRepairButton from '../components/SystemRepairButton';
import { txDirection, txDisplayAmount, txAmountClass, adminTypeLabel } from '../utils/transactions';

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

// User-drawer wallet history with date filter (sorted desc inside the hook)
const DrawerWalletHistory = ({ transactions }) => {
  const { filtered, FilterBar } = useDateRangeFilter(transactions, 'created_at');
  return (
    <div data-testid="drawer-wallet-history">
      <p className="text-xs font-semibold text-slate-700 mb-1">Wallet History ({transactions.length} total)</p>
      {FilterBar}
      {filtered.length === 0 ? (
        <p className="text-xs text-slate-400 text-center py-3" data-testid="drawer-wallet-empty">No transactions in selected range</p>
      ) : (
        <div className="space-y-1 max-h-72 overflow-y-auto">
          {filtered.map((t, i) => {
            const ref = t.reference || {};
            const isOut = txDirection(t) === 'outflow';
            return (
              <div key={t.transaction_id || i} className="bg-slate-50 rounded-lg p-2 text-xs" data-testid={`drawer-txn-${i}`}>
                <div className="flex justify-between items-center gap-2">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-800 truncate">{t.description}</p>
                    <p className="text-[10px] text-slate-400">{t.created_at ? new Date(t.created_at).toLocaleString() : '-'}</p>
                  </div>
                  <span className={`font-semibold whitespace-nowrap ${txAmountClass(t)}`}>{txDisplayAmount(t)}</span>
                </div>
                {(ref.class_title || ref.receipt_id || ref.razorpay_payment_id || ref.counterparty_name) && (
                  <div className="mt-1 pt-1 border-t border-slate-200 text-[10px] text-slate-500 space-y-0.5">
                    {ref.counterparty_name && (
                      <p className={isOut ? 'text-red-500' : 'text-emerald-600'}>
                        {isOut ? '→ paid to' : '← received from'} <span className="font-semibold">{ref.counterparty_name}</span>
                        {ref.counterparty_role && <span className="text-slate-400"> ({ref.counterparty_role})</span>}
                      </p>
                    )}
                    {ref.class_title && <p>📚 {ref.class_title}{ref.class_date ? ` · ${ref.class_date}` : ''}</p>}
                    {ref.receipt_id && <p className="font-mono">Receipt: {ref.receipt_id}</p>}
                    {ref.razorpay_payment_id && <p className="font-mono">RP: {ref.razorpay_payment_id}</p>}
                    {ref.payment_id && (
                      <button
                        onClick={() => {
                          const tk = localStorage.getItem('token');
                          window.open(`${API}/payments/receipt-pdf/${ref.payment_id}?token=${tk}`, '_blank');
                        }}
                        className="underline text-sky-600 hover:text-sky-700"
                        data-testid={`drawer-receipt-${i}`}
                      >View Receipt PDF</button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// Live-editable Email Config — admin can update SMTP without redeploy.
const EmailConfigPanel = () => {
  const [config, setConfig] = useState(null);
  const [senderEmail, setSenderEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [testTo, setTestTo] = useState('');
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const fetchConfig = async () => {
    try {
      const r = await apiFetch(`${API}/admin/email-config`, { credentials: 'include' });
      if (r.ok) {
        const d = await r.json();
        setConfig(d);
        if (!senderEmail) setSenderEmail(d.active_sender_email || '');
        if (!testTo) setTestTo(d.active_sender_email || '');
      }
    } catch {}
  };

  useEffect(() => { fetchConfig(); }, []);

  const save = async () => {
    if (!senderEmail && !appPassword) {
      toast.error('Enter at least sender email or app password'); return;
    }
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-config`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender_email: senderEmail, app_password: appPassword })
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Email config saved');
      setAppPassword('');
      fetchConfig();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  const sendTest = async () => {
    if (!testTo) { toast.error('Enter a recipient'); return; }
    setBusy(true); setTestResult(null);
    try {
      const r = await apiFetch(`${API}/admin/email-test`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to: testTo })
      });
      const d = await r.json();
      setTestResult(d);
      if (d.ok) toast.success(d.message); else toast.error(d.error || 'Test failed');
    } catch (e) { toast.error(e.message); setTestResult({ ok: false, error: e.message }); }
    setBusy(false);
  };

  const clearOverride = async () => {
    if (!window.confirm('Remove DB override and fall back to .env values?')) return;
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/admin/email-config`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_db: true })
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('DB override cleared');
      setAppPassword('');
      fetchConfig();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  return (
    <div className="bg-white rounded-3xl border-2 border-slate-100 p-6" data-testid="email-config-panel">
      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <Mail className="w-5 h-5 text-rose-500" /> Email (Gmail SMTP) Config
      </h3>
      {config && (
        <div className="bg-slate-50 rounded-xl p-3 text-xs space-y-1 mb-3" data-testid="email-config-status">
          <p>Active sender: <strong className="text-slate-800">{config.active_sender_email || '(unset)'}</strong></p>
          <p>Password: {config.password_set ? <span className="text-emerald-700 font-mono">{config.password_masked} ({config.password_length} chars)</span> : <span className="text-red-600">NOT SET</span>}</p>
          <p>Source: <span className={config.source === 'database' ? 'text-violet-700' : 'text-slate-600'}>{config.source}</span></p>
        </div>
      )}
      <div className="space-y-3">
        <div>
          <Label>Sender Email</Label>
          <Input value={senderEmail} onChange={e => setSenderEmail(e.target.value)} placeholder="info@kaimeralearning.com" className="rounded-xl" data-testid="email-config-sender" />
        </div>
        <div>
          <Label>Gmail App Password (16 chars, no spaces)</Label>
          <Input type="password" value={appPassword} onChange={e => setAppPassword(e.target.value)} placeholder="Leave empty to keep current" className="rounded-xl font-mono" data-testid="email-config-password" />
          <p className="text-[11px] text-slate-400 mt-1">Generated at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline text-sky-600">myaccount.google.com/apppasswords</a> — spaces auto-removed when saved.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={save} disabled={busy} className="bg-rose-500 hover:bg-rose-600 text-white rounded-full flex-1" data-testid="email-config-save"><CheckCircle className="w-4 h-4 mr-2" /> Save</Button>
          {config?.source === 'database' && (
            <Button onClick={clearOverride} disabled={busy} variant="outline" className="rounded-full text-xs" data-testid="email-config-clear">Use .env</Button>
          )}
        </div>
        <div className="border-t border-slate-100 pt-3 space-y-2">
          <Label>Send Test Email To</Label>
          <div className="flex gap-2">
            <Input value={testTo} onChange={e => setTestTo(e.target.value)} placeholder="your@email.com" className="rounded-xl flex-1" data-testid="email-test-to" />
            <Button onClick={sendTest} disabled={busy} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="email-test-btn"><Mail className="w-4 h-4 mr-2" /> Test</Button>
          </div>
          {testResult && (
            <div className={`rounded-xl p-3 text-sm ${testResult.ok ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-red-50 text-red-800 border border-red-200'}`} data-testid="email-test-result">
              <p className="font-semibold">{testResult.ok ? '✓ Sent successfully' : '✗ Failed'}</p>
              <p className="text-xs mt-1 break-words">{testResult.message || testResult.error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


// Admin proofs panel: groups by teacher+student, supports date filter, side-by-side compare with previous proof.
const AdminProofsPanel = ({ proofs, onApprove }) => {
  const [teacherFilter, setTeacherFilter] = useState('all');
  const teacherOptions = useMemo(() => {
    const map = new Map();
    for (const p of proofs) {
      if (p.teacher_id && !map.has(p.teacher_id)) {
        map.set(p.teacher_id, p.teacher_details?.name || p.teacher_name || p.teacher_id);
      }
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [proofs]);
  const proofsForFilter = useMemo(() => (
    teacherFilter === 'all' ? proofs : proofs.filter(p => p.teacher_id === teacherFilter)
  ), [proofs, teacherFilter]);
  const { filtered, FilterBar } = useDateRangeFilter(proofsForFilter, 'submitted_at');
  const [open, setOpen] = useState({});
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState({ current: [], archived: [] });
  const [adminNotes, setAdminNotes] = useState('');

  const groups = useMemo(() => {
    const map = new Map();
    for (const p of filtered) {
      const k = `${p.teacher_id}_${p.student_id}`;
      if (!map.has(k)) {
        map.set(k, { key: k, teacher_id: p.teacher_id, teacher_name: p.teacher_details?.name || p.teacher_name, student_name: p.student_details?.name || '-', proofs: [] });
      }
      map.get(k).proofs.push(p);
    }
    const out = [];
    for (const g of map.values()) {
      g.proofs.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
      g.last = g.proofs[0]?.submitted_at;
      out.push(g);
    }
    out.sort((a, b) => new Date(b.last) - new Date(a.last));
    return out;
  }, [filtered]);

  const openDetail = async (p) => {
    setSelected(p);
    setAdminNotes('');
    try {
      const r = await apiFetch(`${API}/counsellor/proof-history/${p.class_id}`, { credentials: 'include' });
      if (r.ok) setHistory(await r.json()); else setHistory({ current: [], archived: [] });
    } catch { setHistory({ current: [], archived: [] }); }
  };

  const previousProof = (() => {
    if (!selected) return null;
    const all = [...history.current, ...history.archived].filter(p => p.proof_id !== selected.proof_id);
    all.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
    return all[0] || null;
  })();
  const isDup = previousProof && selected && previousProof.screenshot_hash && selected.screenshot_hash && previousProof.screenshot_hash === selected.screenshot_hash;

  return (
    <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
      {FilterBar}
      <div className="flex flex-wrap items-center gap-2 mb-4" data-testid="admin-teacher-filter-bar">
        <span className="text-xs font-semibold text-slate-600">Teacher:</span>
        <button
          type="button"
          onClick={() => setTeacherFilter('all')}
          data-testid="admin-teacher-filter-all"
          className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
            teacherFilter === 'all' ? 'bg-violet-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          All Teachers ({teacherOptions.length})
        </button>
        {teacherOptions.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTeacherFilter(t.id)}
            data-testid={`admin-teacher-filter-${t.id}`}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
              teacherFilter === t.id ? 'bg-violet-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {t.name}
          </button>
        ))}
      </div>
      {groups.length === 0 ? (
        <div className="text-center py-12"><Shield className="w-12 h-12 text-slate-300 mx-auto mb-3" /><p className="text-slate-500">No proofs in selected range</p></div>
      ) : (
        <div className="space-y-3">
          {groups.map(g => {
            const isOpen = !!open[g.key];
            return (
              <div key={g.key} className="rounded-2xl border-2 border-slate-200 overflow-hidden" data-testid={`admin-group-${g.key}`}>
                <button onClick={() => setOpen(s => ({ ...s, [g.key]: !s[g.key] }))} className="w-full p-3 flex items-center justify-between hover:bg-slate-50">
                  <div className="text-left">
                    <p className="font-bold text-slate-900 text-sm">{g.teacher_name} → {g.student_name}</p>
                    <p className="text-[11px] text-slate-500">{g.proofs.length} session{g.proofs.length !== 1 ? 's' : ''} · last {g.last ? new Date(g.last).toLocaleString() : '-'}</p>
                  </div>
                  {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </button>
                {isOpen && (
                  <div className="border-t border-slate-100 divide-y divide-slate-100">
                    {g.proofs.map(p => (
                      <button key={p.proof_id} onClick={() => openDetail(p)} className="w-full p-3 flex items-center justify-between text-left hover:bg-slate-50" data-testid={`admin-proof-row-${p.proof_id}`}>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-slate-900 text-sm truncate">{p.class_title}</p>
                            {p.submission_count > 1 && <span className="text-[10px] px-2 rounded-full bg-orange-100 text-orange-700">resubmit #{p.submission_count}</span>}
                            {p.credit_blocked && <span className="text-[10px] px-2 rounded-full bg-red-100 text-red-700">credit blocked</span>}
                          </div>
                          <p className="text-[11px] text-slate-500">{p.proof_date} · {p.meeting_duration_minutes || 0} min</p>
                        </div>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full ${p.admin_status === 'approved' ? 'bg-emerald-100 text-emerald-700' : (p.status === 'rejected' || p.admin_status === 'rejected') ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                          {p.admin_status === 'approved' ? 'APPROVED' : (p.status === 'rejected' || p.admin_status === 'rejected') ? 'REJECTED' : 'AWAITING'}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={v => !v && setSelected(null)}>
        <DialogContent className="sm:max-w-4xl rounded-3xl max-h-[92vh] overflow-y-auto" data-testid="admin-proof-detail">
          <DialogHeader><DialogTitle>Admin Proof Review</DialogTitle></DialogHeader>
          {selected && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Class</p><p className="font-semibold truncate">{selected.class_title}</p></div>
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Teacher</p><p className="font-semibold truncate">{selected.teacher_name}</p></div>
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Real Duration</p><p className="font-semibold">{selected.meeting_duration_minutes || 0} min</p></div>
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Submission</p><p className="font-semibold">#{selected.submission_count || 1}</p></div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Started</p><p className="font-mono">{selected.started_at_actual ? new Date(selected.started_at_actual).toLocaleTimeString() : '-'}</p></div>
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Student Left</p><p className="font-mono">{selected.student_left_at ? new Date(selected.student_left_at).toLocaleTimeString() : '—'}</p></div>
                <div className="bg-slate-50 rounded p-2"><p className="text-slate-500">Teacher Ended</p><p className="font-mono">{selected.ended_at_actual ? new Date(selected.ended_at_actual).toLocaleTimeString() : '-'}</p></div>
              </div>
              {selected.credit_blocked && (
                <div className="bg-red-50 border-2 border-red-200 rounded-xl p-3 text-red-700 text-sm" data-testid="admin-credit-blocked">
                  This proof was rejected twice. Even if approved now, the teacher will NOT be credited.
                </div>
              )}
              {selected.reviewer_notes && (
                <div className="bg-amber-50 border-2 border-amber-200 rounded-xl p-3 text-amber-900 text-sm" data-testid="admin-counsellor-note">
                  <p className="font-semibold text-xs text-amber-800 mb-1">Counsellor Note</p>{selected.reviewer_notes}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-slate-700">Current Submission</p>
                    {isDup && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700" data-testid="admin-duplicate-badge">DUPLICATE</span>}
                    {!isDup && previousProof && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">DIFFERENT</span>}
                  </div>
                  {selected.screenshot_base64
                    ? <img src={selected.screenshot_base64} alt="Current" className="rounded-lg w-full max-h-72 object-contain border" />
                    : <p className="text-xs text-slate-400 italic">No screenshot</p>}
                  <p className="text-[10px] text-slate-400 font-mono break-all mt-1">SHA-256: {selected.screenshot_hash || '-'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-3">
                  <p className="text-xs font-semibold text-slate-700 mb-2">Previous Submission</p>
                  {previousProof ? (
                    <>
                      {previousProof.screenshot_base64
                        ? <img src={previousProof.screenshot_base64} alt="Previous" className="rounded-lg w-full max-h-72 object-contain border" />
                        : <p className="text-xs text-slate-400 italic">No screenshot</p>}
                      <p className="text-[10px] text-slate-400 font-mono break-all mt-1">SHA-256: {previousProof.screenshot_hash || '-'}</p>
                      <p className="text-[10px] text-slate-500">{previousProof.proof_date} · {previousProof.status?.toUpperCase()}</p>
                      {previousProof.reviewer_notes && <p className="text-[10px] italic text-amber-700 mt-1">"{previousProof.reviewer_notes}"</p>}
                    </>
                  ) : <p className="text-xs text-slate-400 italic">No prior proof</p>}
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-3"><p className="text-xs font-semibold text-slate-700 mb-1">Topics Covered</p><p className="text-sm">{selected.topics_covered || '-'}</p></div>
              <div className="bg-slate-50 rounded-xl p-3"><p className="text-xs font-semibold text-slate-700 mb-1">Teacher Feedback</p><p className="text-sm">{selected.feedback_text || '-'}</p></div>

              {selected.admin_status === 'pending' && (
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <Label className="text-xs">Admin Note</Label>
                  <textarea value={adminNotes} onChange={e => setAdminNotes(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} placeholder="Reason for approval / rejection" data-testid="admin-note-input" />
                  <div className="flex gap-3">
                    <Button onClick={() => { onApprove(selected.proof_id, true, adminNotes); setSelected(null); }} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-5 font-bold" data-testid="admin-approve-btn"><Check className="w-4 h-4 mr-2" /> Approve & Credit</Button>
                    <Button onClick={() => { onApprove(selected.proof_id, false, adminNotes); setSelected(null); }} variant="outline" className="flex-1 border-2 border-red-200 text-red-600 rounded-full py-5 font-bold" data-testid="admin-reject-btn"><X className="w-4 h-4 mr-2" /> Reject</Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};


// ─── Main Component ───

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mainTab, setMainTab] = useState('users');
  const [countries, setCountries] = useState([]);
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);

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
  const [txnRoleFilter, setTxnRoleFilter] = useState('admin_own');
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
  const [resetSearchQuery, setResetSearchQuery] = useState('');
  const [resetRoleFilter, setResetRoleFilter] = useState('all');
  const [resetSearchResults, setResetSearchResults] = useState([]);
  const [resetSelectedUser, setResetSelectedUser] = useState(null);

  // Classes
  const [classFilter, setClassFilter] = useState({ search: '', is_demo: '', status: '' });

  // Counsellor chart
  const [expandedCounsellor, setExpandedCounsellor] = useState(null);

  // System Pricing
  const [pricingForm, setPricingForm] = useState({ demo_price_student: '', class_price_student: '', demo_earning_teacher: '', class_earning_teacher: '', cancel_rating_deduction: '', completion_rating_boost: '' });
  const [pricingLoaded, setPricingLoaded] = useState(false);

  // Student Edit
  const [editingStudent, setEditingStudent] = useState(false);
  // Teacher Classes Detail
  const [teacherClasses, setTeacherClasses] = useState(null);
  const [showTeacherClassesDialog, setShowTeacherClassesDialog] = useState(false);
  const [expandedClassId, setExpandedClassId] = useState(null);
  const [editForm, setEditForm] = useState({});

  // Learning Plans
  const [learningPlans, setLearningPlans] = useState([]);
  const [planForm, setPlanForm] = useState({ name: '', price: '', details: '', max_days: '' });
  const [editingPlan, setEditingPlan] = useState(null);

  // Razorpay Payments
  const [razorpayPayments, setRazorpayPayments] = useState([]);
  const [razorpayTotal, setRazorpayTotal] = useState(0);
  const [rpFilterName, setRpFilterName] = useState('');
  const [rpFilterFrom, setRpFilterFrom] = useState('');
  const [rpFilterTo, setRpFilterTo] = useState('');

  useEffect(() => { fetchAll(); }, []);

  // Live polling: refresh admin data every 15s while tab is visible
  useEffect(() => {
    const t = setInterval(() => {
      if (document.visibilityState === 'visible') fetchAll();
    }, 15000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
  setCountries(Country.getAllCountries());
  }, []);

  useEffect(() => {
  if (createForm.country) {
    const st = State.getStatesOfCountry(createForm.country);
    setStates(st);
    setCities([]);
    setCreateForm(prev => ({ ...prev, state: "", city: "" }));
  }
  }, [createForm.country]);

  useEffect(() => {
  if (createForm.state) {
    const ct = City.getCitiesOfState(createForm.country, createForm.state);
    setCities(ct);
    setCreateForm(prev => ({ ...prev, city: "" }));
  }
  }, [createForm.state]);

  const fetchAll = async () => {
    try {
      const [userRes, usersRes, classesRes, txnRes, dailyRes, complaintsRes, proofsRes, tmplRes, trackRes] = await Promise.all([
        apiFetch(`${API}/auth/me`, { credentials: 'include' }),
        apiFetch(`${API}/admin/all-users`, { credentials: 'include' }),
        apiFetch(`${API}/admin/classes`, { credentials: 'include' }),
        apiFetch(`${API}/admin/transactions`, { credentials: 'include' }),
        apiFetch(`${API}/admin/transactions?view=daily&role=all`, { credentials: 'include' }),
        apiFetch(`${API}/admin/complaints`, { credentials: 'include' }),
        apiFetch(`${API}/admin/approved-proofs`, { credentials: 'include' }),
        apiFetch(`${API}/admin/badge-templates`, { credentials: 'include' }),
        apiFetch(`${API}/admin/counsellor-tracking`, { credentials: 'include' })
      ]);
      if (!userRes.ok) throw new Error('Authentication failed. Please log in again.');
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

  const fetchLearningPlans = async () => {
    try {
      const res = await apiFetch(`${API}/admin/learning-plans`, { credentials: 'include' });
      if (res.ok) setLearningPlans(await res.json());
    } catch {}
  };

  const handleSavePlan = async (e) => {
    e.preventDefault();
    if (!planForm.name || !planForm.price || !planForm.details) { toast.error('All fields required'); return; }
    try {
      const url = editingPlan ? `${API}/admin/learning-plans/${editingPlan}` : `${API}/admin/learning-plans`;
      const method = editingPlan ? 'PUT' : 'POST';
      const res = await apiFetch(url, {
        method, credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: planForm.name, price: parseFloat(planForm.price), details: planForm.details, max_days: planForm.max_days ? parseInt(planForm.max_days) : null })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success(editingPlan ? 'Plan updated' : 'Plan created');
      setPlanForm({ name: '', price: '', details: '', max_days: '' });
      setEditingPlan(null);
      fetchLearningPlans();
    } catch (err) { toast.error(err.message); }
  };

  const handleDeletePlan = async (planId) => {
    if (!window.confirm('Deactivate this learning plan?')) return;
    try {
      const res = await apiFetch(`${API}/admin/learning-plans/${planId}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Plan deactivated');
      fetchLearningPlans();
    } catch (err) { toast.error(err.message); }
  };

  const fetchRazorpayPayments = async () => {
    try {
      const params = new URLSearchParams();
      if (rpFilterName) params.set('student_name', rpFilterName);
      if (rpFilterFrom) params.set('date_from', rpFilterFrom);
      if (rpFilterTo) params.set('date_to', rpFilterTo);
      const res = await apiFetch(`${API}/admin/payments?${params}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setRazorpayPayments(data.payments || []);
        setRazorpayTotal(data.total_revenue || 0);
      }
    } catch {}
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!createForm.name || !createForm.email) { toast.error('Name and email required'); return; }
    try {
      const body = { ...createForm, role: createRole, password: 'auto' };
      const res = await apiFetch(`${API}/admin/create-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      toast.success(data.message || 'User created. Credentials emailed to user.');
      setCredsResult({ created: true });  // show "credentials emailed" banner only — never password
      setCreateForm({ name: '', email: '', password: '', phone: '', institute: '', goal: '', preferred_time_slot: '', state: '', city: '', country: '', grade: '' });
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleOpenDrawer = async (userId) => {
    setDrawerData(null);
    const u = allUsers.find(x => x.user_id === userId);
    setDrawerUser(u);
    try {
      const res = await apiFetch(`${API}/admin/user-detail/${userId}`, { credentials: 'include' });
      if (res.ok) setDrawerData(await res.json());
    } catch {}
    // Fetch full profile for teacher/counselor to show extended details + bank info
    if (u && (u.role === 'teacher' || u.role === 'counsellor')) {
      try {
        const endpoint = u.role === 'teacher' ? 'teacher/view-profile' : 'counsellor/view-profile';
        const pRes = await apiFetch(`${API}/${endpoint}/${userId}`, { credentials: 'include' });
        if (pRes.ok) {
          const profileData = await pRes.json();
          setDrawerUser(prev => prev ? { ...prev, ...profileData } : prev);
        }
      } catch {}
    }
  };

  const handleBlock = async (userId, blocked) => {
    if (!window.confirm(`${blocked ? 'Block' : 'Unblock'} this user?`)) return;
    try {
      const res = await apiFetch(`${API}/admin/block-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, blocked })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success(`User ${blocked ? 'blocked' : 'unblocked'}`);
      fetchAll();
    } catch (err) { toast.error(err.message || 'Failed to update user status'); }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('PERMANENTLY delete this user?')) return;
    try {
      const res = await apiFetch(`${API}/admin/delete-user`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('User deleted');
      setDrawerUser(null);
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleResetPassword = async () => {
    const target = resetSelectedUser || (resetEmail ? { email: resetEmail } : null);
    if (!target || !resetPassword) { toast.error('Select a user and enter new password'); return; }
    try {
      const body = { new_password: resetPassword };
      if (target.user_id) body.user_id = target.user_id;
      else if (target.email) body.email = target.email;
      const res = await apiFetch(`${API}/admin/reset-password`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Password reset failed. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'Password reset failed');
      toast.success(`Password reset for ${data.email} (${data.role})`);
      setResetEmail(''); setResetPassword(''); setResetSelectedUser(null); setResetSearchResults([]);
    } catch (err) { toast.error(err.message || 'Failed to reset password'); }
  };

  const handleResetSearch = async () => {
    if (!resetSearchQuery && resetRoleFilter === 'all') return;
    try {
      const res = await apiFetch(`${API}/admin/search-users-for-reset?q=${encodeURIComponent(resetSearchQuery)}&role=${resetRoleFilter}`, { credentials: 'include' });
      if (res.ok) setResetSearchResults(await res.json());
    } catch {}
  };

  const handleAdjustCredits = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch(`${API}/admin/adjust-credits`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: creditUser, amount: parseFloat(creditAmount), action: creditAction })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Credits adjusted');
      setCreditsDialog(false);
      fetchAll();
    } catch { toast.error('Failed to adjust credits'); }
  };

  const handleApproveProof = async (proofId, approved, providedNotes) => {
    const notes = providedNotes !== undefined
      ? providedNotes
      : (approved ? '' : (prompt('Reason for rejection:') || ''));
    try {
      const res = await apiFetch(`${API}/admin/approve-proof`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof_id: proofId, approved, admin_notes: notes })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success(approved ? 'Proof approved & teacher credited!' : 'Proof rejected');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleCreateBadgeTemplate = async () => {
    if (!newTemplateName.trim()) { toast.error('Badge name required'); return; }
    try {
      const res = await apiFetch(`${API}/admin/badge-template`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTemplateName.trim(), description: newTemplateDesc })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Template created');
      setNewTemplateName('');
      setNewTemplateDesc('');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleDeleteBadgeTemplate = async (id) => {
    await apiFetch(`${API}/admin/badge-template/${id}`, { method: 'DELETE', credentials: 'include' });
    fetchAll();
  };

  const handleAssignBadge = async () => {
    const badge = selectedTemplateBadge || badgeName;
    if (!badgeTarget || !badge) { toast.error('Select user and badge'); return; }
    try {
      const res = await apiFetch(`${API}/admin/assign-badge`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: badgeTarget, badge_name: badge })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Badge assigned');
      setBadgeName('');
      setSelectedTemplateBadge('');
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handleFilterTransactions = async () => {
    const params = new URLSearchParams();
    // 'admin_own' = no role param (server defaults to admin's own transactions)
    if (txnRoleFilter && txnRoleFilter !== 'admin_own') params.set('role', txnRoleFilter);
    if (txnDateFrom) params.set('date_from', txnDateFrom);
    if (txnDateTo) params.set('date_to', txnDateTo);
    if (txnSearch) params.set('search', txnSearch);
    if (txnView === 'daily') params.set('view', 'daily');
    try {
      const res = await apiFetch(`${API}/admin/transactions?${params}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        if (txnView === 'daily') setDailyRevenue(data);
        else setTransactions(data);
      }
    } catch { /* ignore network glitch */ }
  };

  // Auto-refetch whenever the role filter or view changes so the displayed table
  // always matches the active filter (no need to click "Apply").
  useEffect(() => {
    handleFilterTransactions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txnRoleFilter, txnView]);

  const fetchTeacherClasses = async (teacherId) => {
    try {
      const res = await apiFetch(`${API}/admin/teacher-classes/${teacherId}`, { credentials: 'include' });
      if (res.ok) {
        setTeacherClasses(await res.json());
        setShowTeacherClassesDialog(true);
        setExpandedClassId(null);
      }
    } catch {}
  };

  const fetchClassDetail = async (classId) => {
    if (expandedClassId === classId) { setExpandedClassId(null); return; }
    try {
      const res = await apiFetch(`${API}/admin/class-detail/${classId}`, { credentials: 'include' });
      if (res.ok) {
        const detail = await res.json();
        // Merge detail into the classes list
        setTeacherClasses(prev => {
          if (!prev) return prev;
          const updated = prev.classes.map(c => c.class_id === classId ? { ...c, _detail: detail } : c);
          return { ...prev, classes: updated };
        });
        setExpandedClassId(classId);
      }
    } catch {}
  };


  const handleApproveTeacher = async (teacherId, approved) => {
    try {
      await apiFetch(`${API}/admin/approve-teacher`, {
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
      const res = await apiFetch(`${API}/admin/counsellor-daily-stats/${cid}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCounsellorDailyStats(prev => ({ ...prev, [cid]: data }));
      }
    } catch {}
  };

  const handleLogout = async () => {
    await apiFetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
    navigate('/login');
  };

  const fetchPricing = async () => {
    try {
      const res = await apiFetch(`${API}/admin/get-pricing`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setPricingForm({
          demo_price_student: data.demo_price_student ?? '',
          class_price_student: data.class_price_student ?? '',
          demo_earning_teacher: data.demo_earning_teacher ?? '',
          class_earning_teacher: data.class_earning_teacher ?? '',
          cancel_rating_deduction: data.cancel_rating_deduction ?? '0.2',
          completion_rating_boost: data.completion_rating_boost ?? '0.1'
        });
        setPricingLoaded(true);
      }
    } catch {}
  };

  const handleSavePricing = async () => {
    try {
      const res = await apiFetch(`${API}/admin/set-pricing`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          demo_price_student: parseFloat(pricingForm.demo_price_student) || 0,
          class_price_student: parseFloat(pricingForm.class_price_student) || 0,
          demo_earning_teacher: parseFloat(pricingForm.demo_earning_teacher) || 0,
          class_earning_teacher: parseFloat(pricingForm.class_earning_teacher) || 0,
          cancel_rating_deduction: parseFloat(pricingForm.cancel_rating_deduction) || 0.2,
          completion_rating_boost: parseFloat(pricingForm.completion_rating_boost) || 0.1
        })
      });
      if (!res.ok) throw new Error(await getApiError(res));
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
      const res = await apiFetch(`${API}/admin/edit-student/${drawerUser.user_id}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Student profile updated!');
      setEditingStudent(false);
      setDrawerUser(null);
      fetchAll();
    } catch (err) { toast.error(err.message); }
  };

  const handlePurgeSystem = async () => {
    if (!window.confirm('WARNING: This will delete ALL students, teachers, counselors, classes, demos, assignments, and pricing. Only the Admin account will remain. This action is IRREVERSIBLE. Are you sure?')) return;
    if (!window.confirm('FINAL CONFIRMATION: Type "yes" to proceed. Everything will be deleted.')) return;
    try {
      const res = await apiFetch(`${API}/admin/purge-system`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
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
              <SystemRepairButton />
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
            <TabsTrigger value="plans" className="rounded-xl px-6 data-[state=active]:bg-amber-500 data-[state=active]:text-white" data-testid="plans-tab" onClick={() => { if (learningPlans.length === 0) fetchLearningPlans(); }}><BookOpen className="w-4 h-4 mr-2" /> Learning Plans</TabsTrigger>
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
                          <h4 className="text-lg font-bold text-emerald-800 mb-3">Account Created — Credentials Emailed</h4>
                          <p className="text-sm text-emerald-700 mb-3">A secure password has been emailed directly to the user. The admin never sees it.</p>
                          <div className="flex gap-2 mt-4">
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
                          <div className="col-span-2 bg-sky-50 border border-sky-200 rounded-xl p-3 text-xs text-sky-800" data-testid="auto-password-hint">
                            🔒 A secure password will be auto-generated and emailed directly to the user. You will not see it.
                          </div>
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
                            <select value={createForm.country} onChange={(e)=>setCreateForm({...createForm,country:e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2">
                            <option value="">Select Country</option>{countries.map(c=><option key={c.isoCode} value={c.isoCode}>{c.name}</option>)}</select>
                            <select value={createForm.state} onChange={(e)=>setCreateForm({...createForm,state:e.target.value})} disabled={!createForm.country} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"><option value="">Select State</option>{states.map(s=><option key={s.isoCode} value={s.isoCode}>{s.name}</option>)}</select>
                            <select value={createForm.city} onChange={(e)=>setCreateForm({...createForm,city:e.target.value})} disabled={!createForm.state} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"><option value="">Select City</option>{cities.map((c,i)=><option key={i} value={c.name}>{c.name}</option>)}</select>
                            <div><Label>Goal</Label><Input value={createForm.goal} onChange={e => setCreateForm({...createForm, goal: e.target.value})} className="rounded-xl" data-testid="create-goal" /></div>
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
                                {u.role === 'teacher' && <Button onClick={() => fetchTeacherClasses(u.user_id)} variant="ghost" size="sm" className="h-7 px-2 text-sky-500" data-testid={`view-classes-${u.user_id}`} title="View Classes"><Calendar className="w-3.5 h-3.5" /></Button>}
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
                  <EmailConfigPanel />
                  <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                    <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><KeyRound className="w-5 h-5 text-amber-500" /> Reset Password</h3>
                    <div className="space-y-3">
                      {/* Search by role or user ID */}
                      <div className="flex gap-2">
                        <select value={resetRoleFilter} onChange={e => setResetRoleFilter(e.target.value)} className="rounded-xl border-2 border-slate-200 px-2 py-2 text-sm" data-testid="reset-role-filter">
                          <option value="all">All Roles</option>
                          <option value="student">Student</option>
                          <option value="teacher">Teacher</option>
                          <option value="counsellor">Counselor</option>
                        </select>
                        <Input value={resetSearchQuery} onChange={e => setResetSearchQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleResetSearch(); }} placeholder="Search by name, email, or User ID..." className="flex-1 rounded-xl" data-testid="reset-search-input" />
                        <Button onClick={handleResetSearch} variant="outline" className="rounded-full" data-testid="reset-search-btn"><Search className="w-4 h-4" /></Button>
                      </div>
                      {/* Search Results */}
                      {resetSearchResults.length > 0 && (
                        <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-xl">
                          {resetSearchResults.map(u => (
                            <div key={u.user_id} onClick={() => { setResetSelectedUser(u); setResetEmail(u.email); }}
                              className={`px-3 py-2 cursor-pointer text-sm hover:bg-sky-50 border-b border-slate-100 ${resetSelectedUser?.user_id === u.user_id ? 'bg-sky-50 border-l-4 border-l-sky-500' : ''}`}
                              data-testid={`reset-user-${u.user_id}`}>
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-semibold text-slate-900">{u.name}</p>
                                  <p className="text-xs text-slate-500">{u.email}</p>
                                </div>
                                <div className="text-right">
                                  <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full">{u.role}</span>
                                  <p className="text-[10px] font-mono text-slate-400 mt-0.5">{u.teacher_code || u.student_code || u.user_id}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {resetSelectedUser && (
                        <div className="bg-sky-50 rounded-xl p-2 text-xs border border-sky-200">
                          Selected: <strong>{resetSelectedUser.name}</strong> ({resetSelectedUser.email}) - {resetSelectedUser.role}
                        </div>
                      )}
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
                <div className="mt-6">
                  <EmailTemplateManager />
                </div>
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ════════════════════════ LEARNING PLANS ════════════════════════ */}
          <TabsContent value="plans">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Create/Edit Form */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2"><BookOpen className="w-5 h-5 text-amber-500" /> {editingPlan ? 'Edit Plan' : 'Create New Plan'}</h3>
                <form onSubmit={handleSavePlan} className="space-y-3">
                  <div>
                    <Label className="text-xs text-slate-600 mb-1 block">Plan Name</Label>
                    <Input value={planForm.name} onChange={e => setPlanForm({ ...planForm, name: e.target.value })} placeholder="e.g. Learning Plan 1" className="rounded-xl" data-testid="plan-name-input" />
                  </div>
                  <div>
                    <Label className="text-xs text-slate-600 mb-1 block">Price (INR)</Label>
                    <Input type="number" step="0.01" value={planForm.price} onChange={e => setPlanForm({ ...planForm, price: e.target.value })} placeholder="e.g. 5000" className="rounded-xl" data-testid="plan-price-input" />
                  </div>
                  <div>
                    <Label className="text-xs text-slate-600 mb-1 block">Details / Syllabus</Label>
                    <textarea value={planForm.details} onChange={e => setPlanForm({ ...planForm, details: e.target.value })} placeholder="Describe the syllabus, topics covered, duration..." className="w-full border border-slate-200 rounded-xl p-3 text-sm min-h-[120px] focus:outline-none focus:ring-2 focus:ring-amber-400" data-testid="plan-details-input" />
                  </div>
                  <div>
                    <Label className="text-xs text-slate-600 mb-1 block">Max Class Days</Label>
                    <Input type="number" min="1" value={planForm.max_days} onChange={e => setPlanForm({ ...planForm, max_days: e.target.value })} placeholder="e.g. 3, 5, 10" className="rounded-xl" data-testid="plan-max-days-input" />
                    <p className="text-[10px] text-slate-500 mt-0.5">Counselor cannot assign more than this many days with this plan</p>
                  </div>
                  <div className="flex gap-2">
                    <Button type="submit" className="flex-1 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-bold" data-testid="save-plan-btn">
                      <Save className="w-4 h-4 mr-2" /> {editingPlan ? 'Update' : 'Create'}
                    </Button>
                    {editingPlan && (
                      <Button type="button" variant="outline" onClick={() => { setEditingPlan(null); setPlanForm({ name: '', price: '', details: '' }); }} className="rounded-xl">Cancel</Button>
                    )}
                  </div>
                </form>
              </div>
              {/* Plans List */}
              <div className="lg:col-span-2">
                <h3 className="font-bold text-slate-900 mb-4">Active Learning Plans ({learningPlans.length})</h3>
                {learningPlans.length === 0 ? (
                  <div className="bg-slate-50 rounded-2xl p-8 text-center text-slate-400">No learning plans yet. Create one to get started.</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {learningPlans.map(p => (
                      <div key={p.plan_id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow" data-testid={`plan-card-${p.plan_id}`}>
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-bold text-slate-900">{p.name}</h4>
                          <span className="text-lg font-black text-amber-600">&#8377;{p.price}</span>
                        </div>
                        <p className="text-sm text-slate-600 mb-4 whitespace-pre-wrap line-clamp-4">{p.details}</p>
                        {p.max_days && <p className="text-xs text-sky-700 font-semibold mb-3">Max Days: {p.max_days}</p>}
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" className="rounded-xl text-xs flex-1" onClick={() => { setEditingPlan(p.plan_id); setPlanForm({ name: p.name, price: p.price, details: p.details, max_days: p.max_days || '' }); }} data-testid={`edit-plan-${p.plan_id}`}>
                            <Pencil className="w-3 h-3 mr-1" /> Edit
                          </Button>
                          <Button variant="outline" size="sm" className="rounded-xl text-xs text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleDeletePlan(p.plan_id)} data-testid={`delete-plan-${p.plan_id}`}>
                            <Trash2 className="w-3 h-3 mr-1" /> Remove
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* ════════════════════════ FINANCIALS ════════════════════════ */}
          <TabsContent value="financials">
            <Tabs defaultValue="ledger">
              <TabsList className="mb-4">
                <TabsTrigger value="ledger" data-testid="ledger-tab">Transaction Ledger</TabsTrigger>
                <TabsTrigger value="razorpay-payments" data-testid="razorpay-payments-tab" onClick={() => fetchRazorpayPayments()}><IndianRupee className="w-3.5 h-3.5 mr-1" /> Razorpay Payments</TabsTrigger>
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
                      {[
                        { v: 'admin_own', label: 'My Wallet' },
                        { v: 'all', label: 'All Users' },
                        { v: 'student', label: 'Student' },
                        { v: 'teacher', label: 'Teacher' },
                        { v: 'counsellor', label: 'Counsellor' },
                      ].map(r => (
                        <button key={r.v} onClick={() => setTxnRoleFilter(r.v)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${txnRoleFilter === r.v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`} data-testid={`txn-filter-${r.v}`}>{r.label}</button>
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
                            {txnRoleFilter !== 'admin_own' && (
                              <>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">User</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Role</th>
                              </>
                            )}
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Type</th>
                            {txnRoleFilter === 'admin_own' && (
                              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Counterparty</th>
                            )}
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600">Amount</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Description / Reference</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Date</th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600">Receipt</th>
                          </tr>
                        </thead>
                        <tbody>
                          {transactions.slice(0, 100).map((txn, i) => {
                            const ref = txn.reference || {};
                            const isAdminView = txnRoleFilter === 'admin_own';
                            const isOut = txDirection(txn) === 'outflow';
                            return (
                              <tr key={txn.transaction_id || i} className="border-t border-slate-100 hover:bg-slate-50 align-top" data-testid={`txn-row-${i}`}>
                                {!isAdminView && (
                                  <>
                                    <td className="px-4 py-3">
                                      <button onClick={() => txn.user_id && handleOpenDrawer(txn.user_id)} className="text-sm font-medium text-slate-900 hover:text-sky-600">{txn.user_name || 'Unknown'}</button>
                                      <p className="text-xs text-slate-400 font-mono">{txn.user_code}</p>
                                    </td>
                                    <td className="px-4 py-3"><RoleBadge role={txn.user_role} /></td>
                                  </>
                                )}
                                <td className="px-4 py-3 text-xs">
                                  {isAdminView ? (
                                    <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold ${isOut ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
                                      {adminTypeLabel(txn.type)}
                                    </span>
                                  ) : (
                                    <span className="text-slate-500">{txn.type}</span>
                                  )}
                                </td>
                                {isAdminView && (
                                  <td className="px-4 py-3 text-xs">
                                    {ref.counterparty_name ? (
                                      <button onClick={() => ref.counterparty_user_id && handleOpenDrawer(ref.counterparty_user_id)} className="text-left">
                                        <p className="font-semibold text-slate-800 hover:text-sky-600">{ref.counterparty_name}</p>
                                        {ref.counterparty_role && <p className="text-[11px] text-slate-400 capitalize">{ref.counterparty_role}</p>}
                                      </button>
                                    ) : <span className="text-slate-300">—</span>}
                                  </td>
                                )}
                                <td className={`px-4 py-3 text-sm text-right font-bold ${txAmountClass(txn)}`}>{txDisplayAmount(txn)}</td>
                                <td className="px-4 py-3 text-sm text-slate-600 max-w-[260px]">
                                  <p className="truncate">{txn.description}</p>
                                  {!isAdminView && ref.counterparty_name && (
                                    <p className={`text-[11px] mt-0.5 ${isOut ? 'text-red-500' : 'text-emerald-600'}`}>
                                      {isOut ? '→ paid to' : '← received from'} <span className="font-semibold">{ref.counterparty_name}</span>
                                      {ref.counterparty_role && <span className="text-slate-400"> ({ref.counterparty_role})</span>}
                                    </p>
                                  )}
                                  {ref.class_title && <p className="text-[11px] text-slate-500 mt-0.5">📚 {ref.class_title}{ref.class_date ? ` · ${ref.class_date}` : ''}{ref.teacher_name ? ` · ${ref.teacher_name}` : ''}</p>}
                                  {ref.receipt_id && <p className="text-[10px] font-mono text-slate-400">{ref.receipt_id}</p>}
                                  {ref.razorpay_payment_id && <p className="text-[10px] font-mono text-slate-400">RP: {ref.razorpay_payment_id}</p>}
                                </td>
                                <td className="px-4 py-3 text-xs text-slate-400">{txn.created_at?.slice(0, 10)}</td>
                                <td className="px-4 py-3 text-center">
                                  {ref.payment_id ? (
                                    <Button variant="outline" size="sm" className="rounded-full h-7 px-3" onClick={() => {
                                      const t = localStorage.getItem('token');
                                      window.open(`${API}/payments/receipt-pdf/${ref.payment_id}?token=${t}`, '_blank');
                                    }} data-testid={`txn-receipt-${i}`}><Download className="w-3 h-3" /></Button>
                                  ) : <span className="text-[11px] text-slate-300">—</span>}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* ── Razorpay Payments ── */}
              <TabsContent value="razorpay-payments">
                <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
                  <div className="flex flex-wrap gap-3 items-end mb-4">
                    <div className="flex-1 min-w-[200px]">
                      <Label className="text-xs text-slate-500">Student Name</Label>
                      <Input value={rpFilterName} onChange={e => setRpFilterName(e.target.value)} placeholder="Search by student name..." className="rounded-xl" data-testid="rp-filter-name" />
                    </div>
                    <div>
                      <Label className="text-xs text-slate-500">From</Label>
                      <Input type="date" value={rpFilterFrom} onChange={e => setRpFilterFrom(e.target.value)} className="rounded-xl w-40" data-testid="rp-filter-from" />
                    </div>
                    <div>
                      <Label className="text-xs text-slate-500">To</Label>
                      <Input type="date" value={rpFilterTo} onChange={e => setRpFilterTo(e.target.value)} className="rounded-xl w-40" data-testid="rp-filter-to" />
                    </div>
                    <Button onClick={fetchRazorpayPayments} className="bg-sky-500 text-white rounded-xl" data-testid="rp-apply-filter"><Filter className="w-4 h-4 mr-1" /> Apply</Button>
                  </div>
                  <div className="bg-emerald-50 rounded-2xl p-4 mb-4 flex items-center justify-between">
                    <span className="text-sm text-emerald-800 font-semibold">Total Revenue (Paid)</span>
                    <span className="text-2xl font-black text-emerald-700" data-testid="rp-total-revenue">&#8377;{razorpayTotal.toLocaleString()}</span>
                  </div>
                  <div className="overflow-x-auto max-h-[50vh] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="text-left p-2 text-xs text-slate-500">Date</th>
                          <th className="text-left p-2 text-xs text-slate-500">Student</th>
                          <th className="text-left p-2 text-xs text-slate-500">Teacher</th>
                          <th className="text-left p-2 text-xs text-slate-500">Plan</th>
                          <th className="text-right p-2 text-xs text-slate-500">Amount</th>
                          <th className="text-center p-2 text-xs text-slate-500">Status</th>
                          <th className="text-left p-2 text-xs text-slate-500">Receipt</th>
                        </tr>
                      </thead>
                      <tbody>
                        {razorpayPayments.map(p => (
                          <tr key={p.payment_id} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="p-2 text-xs">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '-'}</td>
                            <td className="p-2"><p className="font-semibold text-xs">{p.student_name}</p><p className="text-[10px] text-slate-400">{p.student_email}</p></td>
                            <td className="p-2 text-xs">{p.teacher_name}</td>
                            <td className="p-2 text-xs">{p.learning_plan_name || '-'}</td>
                            <td className="p-2 text-right font-bold text-xs">&#8377;{p.amount}</td>
                            <td className="p-2 text-center">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${p.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{p.status}</span>
                            </td>
                            <td className="p-2 text-xs font-mono">{p.receipt_id || '-'}</td>
                          </tr>
                        ))}
                        {razorpayPayments.length === 0 && (
                          <tr><td colSpan="7" className="text-center p-8 text-slate-400">No payments found</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </TabsContent>

              {/* ── Proofs & Approvals ── */}
              <TabsContent value="proofs">
                <AdminProofsPanel proofs={pendingProofs} onApprove={(proofId, approved, notes) => handleApproveProof(proofId, approved, notes)} />
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
                    {/* Rating Settings */}
                    <div className="bg-red-50 rounded-xl p-4 border border-red-200 mt-4">
                      <h4 className="text-sm font-bold text-red-800 mb-2">Teacher Cancellation Penalty</h4>
                      <div>
                        <Label className="text-xs text-red-700">Rating Deducted Per Cancellation</Label>
                        <Input type="number" step="0.1" min="0" max="2" value={pricingForm.cancel_rating_deduction} onChange={e => setPricingForm({...pricingForm, cancel_rating_deduction: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-cancel-deduction" />
                        <p className="text-[10px] text-slate-500 mt-1">Points deducted from teacher rating each time they cancel a session (default 0.2)</p>
                      </div>
                    </div>
                    <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200 mt-4">
                      <h4 className="text-sm font-bold text-emerald-800 mb-2">Successful Completion Reward</h4>
                      <div>
                        <Label className="text-xs text-emerald-700">Rating Boost Per Completion</Label>
                        <Input type="number" step="0.1" min="0" max="1" value={pricingForm.completion_rating_boost} onChange={e => setPricingForm({...pricingForm, completion_rating_boost: e.target.value})} className="rounded-xl bg-white" data-testid="pricing-completion-boost" />
                        <p className="text-[10px] text-slate-500 mt-1">Points added to teacher rating when all classes are completed with proofs approved (max rating: 5.0)</p>
                      </div>
                    </div>
                    <Button onClick={handleSavePricing} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold mt-4" data-testid="save-pricing-btn">
                      <Save className="w-5 h-5 mr-2" /> Save System Pricing
                    </Button>
                  </div>
                  {/* System Reset */}
                  <div className="mt-8 bg-red-50 rounded-2xl p-5 border border-red-200">
                    <h4 className="text-sm font-bold text-red-800 mb-2">Danger Zone</h4>
                    <p className="text-xs text-red-600 mb-3">Purge all system data (students, teachers, counselors, classes, demos, pricing). Only Admin account will remain. This is irreversible.</p>
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
                <TabsTrigger value="counsellors" data-testid="counsellors-report-tab">Counselor Tracking</TabsTrigger>
                <TabsTrigger value="classes" data-testid="classes-report-tab">Class Overview</TabsTrigger>
                <TabsTrigger value="complaints" data-testid="complaints-report-tab">Complaints ({complaints.length})</TabsTrigger>
              </TabsList>

              {/* ── Counselor Tracking ── */}
              <TabsContent value="counsellors">
                {counsellorTracking.length === 0 ? (
                  <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center"><p className="text-slate-500">No counselors found</p></div>
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
                  {/* Profile Info Grid */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">Credits</p><p className="text-lg font-bold">{drawerUser.credits || 0}</p></div>
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">Phone</p><p className="text-xs font-medium">{drawerUser.phone || 'N/A'}</p></div>
                    <div className="bg-slate-50 rounded-xl p-2 text-center"><p className="text-[10px] text-slate-500">{drawerUser.role === 'teacher' ? 'KLAT' : drawerUser.role === 'counsellor' ? 'KL-CAT' : 'Grade'}</p><p className="text-xs font-medium">{drawerUser.klat_score || drawerUser.klcat_score || (drawerUser.grade ? `Class ${drawerUser.grade}` : 'N/A')}</p></div>
                  </div>
                  {/* Extended Profile Details */}
                  {(drawerUser.bio || drawerUser.education_qualification || drawerUser.teaching_experience || drawerUser.experience || drawerUser.address || drawerUser.date_of_birth) && (
                    <div className="grid grid-cols-2 gap-2">
                      {drawerUser.profile_picture && <div className="col-span-2 flex justify-center"><img src={drawerUser.profile_picture} alt="" className="w-20 h-20 rounded-full object-cover border-2 border-slate-200" /></div>}
                      {drawerUser.bio && <div className="col-span-2 bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Bio</p><p className="text-xs">{drawerUser.bio}</p></div>}
                      {drawerUser.age && <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Age</p><p className="text-xs font-medium">{drawerUser.age}</p></div>}
                      {drawerUser.date_of_birth && <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">DOB</p><p className="text-xs font-medium">{drawerUser.date_of_birth}</p></div>}
                      {drawerUser.education_qualification && <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Education</p><p className="text-xs font-medium">{drawerUser.education_qualification}</p></div>}
                      {drawerUser.address && <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Address</p><p className="text-xs font-medium">{drawerUser.address}</p></div>}
                      {drawerUser.interests_hobbies && <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Interests</p><p className="text-xs font-medium">{drawerUser.interests_hobbies}</p></div>}
                      {(drawerUser.teaching_experience || drawerUser.experience) && <div className="col-span-2 bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Experience</p><p className="text-xs">{drawerUser.teaching_experience || drawerUser.experience}</p></div>}
                    </div>
                  )}
                  {/* Bank Details - Admin only */}
                  {(drawerUser.role === 'teacher' || drawerUser.role === 'counsellor') && drawerUser.bank_name && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                      <p className="text-xs font-bold text-amber-800 mb-2">Bank Details (Admin Only)</p>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div><p className="text-[10px] text-amber-600">Bank</p><p className="font-medium">{drawerUser.bank_name}</p></div>
                        <div><p className="text-[10px] text-amber-600">A/C No</p><p className="font-medium">{drawerUser.bank_account_number}</p></div>
                        <div><p className="text-[10px] text-amber-600">IFSC</p><p className="font-medium">{drawerUser.bank_ifsc_code}</p></div>
                      </div>
                    </div>
                  )}
                  {/* Resume */}
                  {drawerUser.resume_name && (
                    <div className="bg-sky-50 border border-sky-200 rounded-xl p-2 flex items-center gap-2 text-xs">
                      <span className="font-medium text-sky-800">{drawerUser.resume_name}</span>
                      {drawerUser.resume_base64 && <a href={drawerUser.resume_base64} target="_blank" rel="noreferrer" className="ml-auto text-sky-600 hover:underline">View</a>}
                    </div>
                  )}
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
                    <DrawerWalletHistory transactions={drawerData.transactions} />
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

      {/* Teacher Classes Detail Dialog */}
      <Dialog open={showTeacherClassesDialog} onOpenChange={setShowTeacherClassesDialog}>
        <DialogContent className="sm:max-w-4xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-amber-500" /> {teacherClasses?.teacher?.name}'s Classes
            </DialogTitle>
          </DialogHeader>
          {teacherClasses && (
            <div className="mt-4 space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-slate-50 rounded-xl p-3 text-center"><p className="text-2xl font-bold">{teacherClasses.summary.total_classes}</p><p className="text-[10px] text-slate-500">Total</p></div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center"><p className="text-2xl font-bold text-emerald-700">{teacherClasses.summary.completed}</p><p className="text-[10px] text-slate-500">Completed</p></div>
                <div className="bg-sky-50 rounded-xl p-3 text-center"><p className="text-2xl font-bold text-sky-700">{teacherClasses.summary.scheduled}</p><p className="text-[10px] text-slate-500">Active</p></div>
                <div className="bg-amber-50 rounded-xl p-3 text-center"><p className="text-2xl font-bold text-amber-700">{teacherClasses.summary.transferred}</p><p className="text-[10px] text-slate-500">Transferred</p></div>
              </div>

              {/* Classes list — clickable to expand */}
              <div className="space-y-2">
                {teacherClasses.classes.map(cls => (
                  <div key={cls.class_id} className="border border-slate-200 rounded-xl overflow-hidden">
                    <button onClick={() => fetchClassDetail(cls.class_id)}
                      className="w-full p-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left" data-testid={`class-row-${cls.class_id}`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-8 rounded-full ${cls.status === 'completed' ? 'bg-emerald-400' : cls.status === 'scheduled' ? 'bg-sky-400' : cls.status === 'in_progress' ? 'bg-emerald-500' : cls.status === 'transferred' ? 'bg-amber-400' : 'bg-red-400'}`}></div>
                        <div>
                          <p className="font-semibold text-sm text-slate-900">{cls.title}</p>
                          <p className="text-xs text-slate-500">{cls.date} to {cls.end_date} | {cls.start_time}-{cls.end_time} | {cls.duration_days}d</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-emerald-700 font-semibold">{cls.sessions_conducted || 0}/{cls.duration_days}d done</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${cls.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : cls.status === 'scheduled' ? 'bg-sky-100 text-sky-700' : cls.status === 'transferred' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'}`}>{cls.status}</span>
                        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${expandedClassId === cls.class_id ? 'rotate-180' : ''}`} />
                      </div>
                    </button>

                    {/* Expanded detail */}
                    {expandedClassId === cls.class_id && cls._detail && (
                      <div className="border-t border-slate-200 p-4 bg-slate-50 space-y-3">
                        {/* Session Timeline */}
                        <div>
                          <p className="text-xs font-bold text-slate-700 mb-1">Session Timeline</p>
                          {(cls._detail.session_history || []).length > 0 ? (
                            <div className="space-y-1">
                              {cls._detail.session_history.map((s, i) => (
                                <div key={i} className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${s.status === 'conducted' ? 'bg-emerald-50' : 'bg-red-50'}`}>
                                  <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'conducted' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                                  <span className="font-medium">{s.date}</span>
                                  <span className={s.status === 'conducted' ? 'text-emerald-700' : 'text-red-700'}>{s.status.replace(/_/g, ' ')}</span>
                                  {s.reason && <span className="text-slate-500">({s.reason})</span>}
                                </div>
                              ))}
                            </div>
                          ) : <p className="text-xs text-slate-400">No sessions yet</p>}
                        </div>

                        {/* Attendance */}
                        <div>
                          <p className="text-xs font-bold text-slate-700 mb-1">Attendance ({(cls._detail.attendance || []).length})</p>
                          {(cls._detail.attendance || []).length > 0 ? (
                            <div className="grid grid-cols-2 gap-1">
                              {cls._detail.attendance.map((a, i) => (
                                <div key={i} className="flex items-center justify-between text-xs bg-white rounded px-2 py-1">
                                  <span>{a.date} — {a.student_name}</span>
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${a.status === 'present' ? 'bg-emerald-100 text-emerald-700' : a.status === 'absent' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{a.status}</span>
                                </div>
                              ))}
                            </div>
                          ) : <p className="text-xs text-slate-400">No records</p>}
                        </div>

                        {/* Proofs */}
                        <div>
                          <p className="text-xs font-bold text-slate-700 mb-1">Proofs ({(cls._detail.proofs || []).length})</p>
                          {(cls._detail.proofs || []).length > 0 ? (
                            <div className="space-y-1">
                              {cls._detail.proofs.map((p, i) => (
                                <div key={i} className="flex items-center justify-between text-xs bg-white rounded px-2 py-1">
                                  <div>
                                    <span className="font-medium">{p.proof_date}</span>
                                    {p.meeting_duration_minutes > 0 && <span className="text-slate-500 ml-2">({Math.round(p.meeting_duration_minutes)} min)</span>}
                                  </div>
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${p.admin_status === 'approved' ? 'bg-emerald-100 text-emerald-700' : p.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>{p.admin_status || p.status}</span>
                                </div>
                              ))}
                            </div>
                          ) : <p className="text-xs text-slate-400">No proofs</p>}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
