import { getApiError, API } from '../utils/api';
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, CheckCircle, XCircle, Clock, FileText, Image as ImageIcon, ChevronDown, ChevronUp, AlertTriangle, History } from 'lucide-react';
import { useDateRangeFilter } from '../components/DateRangeFilter';
import { useLivePoll } from '../hooks/useLivePoll';

const Pill = ({ children, color = 'slate' }) => (
  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold bg-${color}-100 text-${color}-800`}>{children}</span>
);

const CounsellorProofs = () => {
  const navigate = useNavigate();
  const [pendingProofs, setPendingProofs] = useState([]);
  const [allProofs, setAllProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProof, setSelectedProof] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [viewMode, setViewMode] = useState('pending');
  const [history, setHistory] = useState({ current: [], archived: [] });
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expanded, setExpanded] = useState({});  // assignment_key -> bool

  useEffect(() => { fetchProofs(); }, []);
  useLivePoll(fetchProofs, 15000);

  async function fetchProofs() {
    try {
      const [pendingRes, allRes] = await Promise.all([
        fetch(`${API}/counsellor/pending-proofs`, { credentials: 'include' }),
        fetch(`${API}/counsellor/all-proofs`, { credentials: 'include' })
      ]);
      if (pendingRes.ok) setPendingProofs(await pendingRes.json());
      if (allRes.ok) setAllProofs(await allRes.json());
      setLoading(false);
    } catch {
      toast.error('Failed to load proofs');
      setLoading(false);
    }
  }

  const handleVerify = async (approved) => {
    try {
      const response = await fetch(`${API}/counsellor/verify-proof`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ proof_id: selectedProof.proof_id, approved, reviewer_notes: reviewerNotes })
      });
      if (!response.ok) throw new Error(await getApiError(response));
      toast.success(`Proof ${approved ? 'approved' : 'rejected'}!`);
      setShowDetailDialog(false);
      setSelectedProof(null);
      setReviewerNotes('');
      fetchProofs();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const openDetail = async (proof) => {
    setSelectedProof(proof);
    setShowDetailDialog(true);
    setReviewerNotes('');
    setHistoryLoading(true);
    try {
      const r = await fetch(`${API}/counsellor/proof-history/${proof.class_id}`, { credentials: 'include' });
      if (r.ok) setHistory(await r.json());
      else setHistory({ current: [], archived: [] });
    } catch { setHistory({ current: [], archived: [] }); }
    setHistoryLoading(false);
  };

  const sourceProofs = viewMode === 'pending' ? pendingProofs : allProofs;
  const { filtered, FilterBar } = useDateRangeFilter(sourceProofs, 'submitted_at');

  // Group by assignment_key = teacher_id + "_" + student_id
  const groups = useMemo(() => {
    const map = new Map();
    for (const p of filtered) {
      const k = `${p.teacher_id}_${p.student_id}`;
      if (!map.has(k)) {
        map.set(k, {
          key: k,
          teacher_id: p.teacher_id, teacher_name: p.teacher_name,
          student_id: p.student_id,
          proofs: []
        });
      }
      map.get(k).proofs.push(p);
    }
    // For each group, sort sessions desc by submitted_at; collect counts
    const out = [];
    for (const g of map.values()) {
      g.proofs.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
      g.counts = {
        pending: g.proofs.filter(p => p.status === 'pending').length,
        rejected: g.proofs.filter(p => p.status === 'rejected' || p.admin_status === 'rejected').length,
        approved: g.proofs.filter(p => p.admin_status === 'approved').length,
        verified: g.proofs.filter(p => p.status === 'verified').length,
      };
      g.last_submitted = g.proofs[0]?.submitted_at || '';
      out.push(g);
    }
    // Newest activity first
    out.sort((a, b) => new Date(b.last_submitted) - new Date(a.last_submitted));
    return out;
  }, [filtered]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  // Find the previous (different) screenshot from same class to compare side-by-side
  const previousProof = (() => {
    if (!selectedProof) return null;
    const all = [...history.current, ...history.archived]
      .filter(p => p.proof_id !== selectedProof.proof_id)
      .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
    return all[0] || null;
  })();
  const isDuplicateScreenshot = previousProof && selectedProof &&
    previousProof.screenshot_hash && selectedProof.screenshot_hash &&
    previousProof.screenshot_hash === selectedProof.screenshot_hash;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-4">
          <Button onClick={() => navigate('/counsellor-dashboard')} variant="outline" className="rounded-full">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          <h1 className="text-2xl font-bold text-slate-900">Class Verifications</h1>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-3 mb-4">
          <Button onClick={() => setViewMode('pending')}
            className={`rounded-full ${viewMode === 'pending' ? 'bg-amber-500 text-white' : 'bg-white text-slate-700 border-2 border-slate-200'}`}
            data-testid="pending-proofs-tab">
            <Clock className="w-4 h-4 mr-2" /> Pending ({pendingProofs.length})
          </Button>
          <Button onClick={() => setViewMode('all')}
            className={`rounded-full ${viewMode === 'all' ? 'bg-sky-500 text-white' : 'bg-white text-slate-700 border-2 border-slate-200'}`}
            data-testid="all-proofs-tab">
            <FileText className="w-4 h-4 mr-2" /> All Proofs ({allProofs.length})
          </Button>
        </div>

        {FilterBar}

        {groups.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center" data-testid="proofs-empty">
            <p className="text-slate-600">{viewMode === 'pending' ? 'No pending proofs' : 'No proofs in selected range'}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {groups.map(group => {
              const open = !!expanded[group.key];
              return (
                <div key={group.key} className="bg-white rounded-2xl border-2 border-slate-200 overflow-hidden" data-testid={`group-${group.key}`}>
                  <button onClick={() => setExpanded(s => ({ ...s, [group.key]: !s[group.key] }))}
                    className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition">
                    <div className="text-left">
                      <p className="font-bold text-slate-900">{group.teacher_name}</p>
                      <p className="text-xs text-slate-500">{group.proofs.length} session{group.proofs.length !== 1 ? 's' : ''} · last: {group.last_submitted ? new Date(group.last_submitted).toLocaleString() : '-'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {group.counts.pending > 0 && <Pill color="amber">{group.counts.pending} pending</Pill>}
                      {group.counts.verified > 0 && <Pill color="violet">{group.counts.verified} forwarded</Pill>}
                      {group.counts.approved > 0 && <Pill color="emerald">{group.counts.approved} approved</Pill>}
                      {group.counts.rejected > 0 && <Pill color="red">{group.counts.rejected} rejected</Pill>}
                      {open ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                    </div>
                  </button>
                  {open && (
                    <div className="border-t border-slate-100 divide-y divide-slate-100">
                      {group.proofs.map(proof => (
                        <button key={proof.proof_id} onClick={() => openDetail(proof)}
                          className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50 transition"
                          data-testid={`proof-row-${proof.proof_id}`}>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="font-semibold text-slate-900 text-sm truncate">{proof.class_title}</p>
                              {proof.submission_count > 1 && <Pill color="orange">resubmission #{proof.submission_count}</Pill>}
                              {proof.credit_blocked && <Pill color="red">credit blocked</Pill>}
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">
                              {proof.proof_date} · {proof.meeting_duration_minutes ? `${proof.meeting_duration_minutes} min` : 'duration n/a'} · perf: {proof.student_performance || 'n/a'}
                            </p>
                          </div>
                          <Pill color={proof.admin_status === 'approved' ? 'emerald' : (proof.status === 'rejected' || proof.admin_status === 'rejected') ? 'red' : proof.status === 'verified' ? 'violet' : 'amber'}>
                            {proof.admin_status === 'approved' ? 'APPROVED' : (proof.status === 'rejected' || proof.admin_status === 'rejected') ? 'REJECTED' : proof.status === 'verified' ? 'TO ADMIN' : 'PENDING'}
                          </Pill>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail dialog with side-by-side compare */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-4xl rounded-3xl max-h-[92vh] overflow-y-auto" data-testid="proof-detail-dialog">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Proof Review</DialogTitle>
          </DialogHeader>
          {selectedProof && (
            <div className="space-y-4 mt-2">
              {/* Quick facts */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Class</p><p className="font-semibold truncate">{selectedProof.class_title}</p></div>
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Teacher</p><p className="font-semibold truncate">{selectedProof.teacher_name}</p></div>
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Real Duration</p><p className="font-semibold">{selectedProof.meeting_duration_minutes || 0} min</p></div>
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Submission</p><p className="font-semibold">#{selectedProof.submission_count || 1}</p></div>
              </div>
              {/* Started/Ended timestamps for accountability */}
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Class Started At</p><p className="font-mono">{selectedProof.started_at_actual ? new Date(selectedProof.started_at_actual).toLocaleTimeString() : '-'}</p></div>
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Student Left At</p><p className="font-mono">{selectedProof.student_left_at ? new Date(selectedProof.student_left_at).toLocaleTimeString() : '—'}</p></div>
                <div className="bg-slate-50 rounded-lg p-2"><p className="text-slate-500">Teacher Ended At</p><p className="font-mono">{selectedProof.ended_at_actual ? new Date(selectedProof.ended_at_actual).toLocaleTimeString() : '-'}</p></div>
              </div>

              {selectedProof.credit_blocked && (
                <div className="bg-red-50 border-2 border-red-200 rounded-xl p-3 flex items-center gap-2 text-red-700 text-sm" data-testid="credit-blocked-banner">
                  <AlertTriangle className="w-4 h-4" /> This proof was rejected twice. Even if approved now, the teacher will NOT be credited for this session.
                </div>
              )}

              {/* Side-by-side: current vs previous */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-slate-700">Current Submission</p>
                    {isDuplicateScreenshot && <Pill color="red" data-testid="duplicate-badge">DUPLICATE SCREENSHOT</Pill>}
                    {!isDuplicateScreenshot && previousProof && <Pill color="emerald">DIFFERENT SCREENSHOT</Pill>}
                  </div>
                  {selectedProof.screenshot_base64 ? (
                    <img src={selectedProof.screenshot_base64} alt="Current proof" className="rounded-lg w-full max-h-72 object-contain border" />
                  ) : <p className="text-xs text-slate-400 italic">No screenshot attached</p>}
                  <p className="text-[10px] text-slate-400 mt-1 font-mono break-all">SHA-256: {selectedProof.screenshot_hash || 'n/a'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-slate-700 flex items-center gap-1"><History className="w-3.5 h-3.5" /> Previous Submission</p>
                    {historyLoading && <span className="text-[10px] text-slate-400">loading…</span>}
                  </div>
                  {previousProof ? (
                    <>
                      {previousProof.screenshot_base64 ? (
                        <img src={previousProof.screenshot_base64} alt="Previous proof" className="rounded-lg w-full max-h-72 object-contain border" />
                      ) : <p className="text-xs text-slate-400 italic">No screenshot</p>}
                      <p className="text-[10px] text-slate-400 mt-1 font-mono break-all">SHA-256: {previousProof.screenshot_hash || 'n/a'}</p>
                      <p className="text-[10px] text-slate-500 mt-1">{previousProof.proof_date} · {previousProof.status?.toUpperCase()}{previousProof.admin_status ? ' / ' + previousProof.admin_status.toUpperCase() : ''}</p>
                      {previousProof.reviewer_notes && <p className="text-[10px] text-amber-700 italic mt-1">"{previousProof.reviewer_notes}"</p>}
                    </>
                  ) : <p className="text-xs text-slate-400 italic">No prior proof for this class</p>}
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-3">
                <p className="text-xs font-semibold text-slate-700 mb-1">Topics Covered</p>
                <p className="text-sm">{selectedProof.topics_covered || '-'}</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3">
                <p className="text-xs font-semibold text-slate-700 mb-1">Teacher's Feedback</p>
                <p className="text-sm">{selectedProof.feedback_text || '-'}</p>
              </div>

              {selectedProof.status === 'pending' && (
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <Label className="text-xs">Reviewer Notes (visible to teacher and admin)</Label>
                  <textarea
                    value={reviewerNotes}
                    onChange={e => setReviewerNotes(e.target.value)}
                    className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"
                    rows={3}
                    placeholder="Why are you approving / rejecting?"
                    data-testid="reviewer-notes-input"
                  />
                  <div className="flex gap-3">
                    <Button onClick={() => handleVerify(true)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-5 font-bold" data-testid="approve-proof-button">
                      <CheckCircle className="w-5 h-5 mr-2" /> Approve & Forward to Admin
                    </Button>
                    <Button onClick={() => handleVerify(false)} variant="outline" className="flex-1 border-2 border-red-200 text-red-600 hover:bg-red-50 rounded-full py-5 font-bold" data-testid="reject-proof-button">
                      <XCircle className="w-5 h-5 mr-2" /> Reject
                    </Button>
                  </div>
                </div>
              )}

              {selectedProof.status !== 'pending' && selectedProof.reviewer_notes && (
                <div className="bg-amber-50 rounded-xl p-3 border-2 border-amber-200">
                  <p className="text-xs text-amber-800 font-semibold mb-1">Counsellor Note</p>
                  <p className="text-amber-900 text-sm">{selectedProof.reviewer_notes}</p>
                </div>
              )}
              {selectedProof.admin_notes && (
                <div className="bg-violet-50 rounded-xl p-3 border-2 border-violet-200">
                  <p className="text-xs text-violet-800 font-semibold mb-1">Admin Note</p>
                  <p className="text-violet-900 text-sm">{selectedProof.admin_notes}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CounsellorProofs;
