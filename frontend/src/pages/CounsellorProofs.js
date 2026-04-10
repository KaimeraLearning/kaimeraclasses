import { getApiError } from '../utils/api';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, CheckCircle, XCircle, Clock, FileText, Image } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CounsellorProofs = () => {
  const navigate = useNavigate();
  const [pendingProofs, setPendingProofs] = useState([]);
  const [allProofs, setAllProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProof, setSelectedProof] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [viewMode, setViewMode] = useState('pending');

  useEffect(() => { fetchProofs(); }, []);

  const fetchProofs = async () => {
    try {
      const [pendingRes, allRes] = await Promise.all([
        fetch(`${API}/counsellor/pending-proofs`, { credentials: 'include' }),
        fetch(`${API}/counsellor/all-proofs`, { credentials: 'include' })
      ]);
      if (pendingRes.ok) setPendingProofs(await pendingRes.json());
      if (allRes.ok) setAllProofs(await allRes.json());
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load proofs');
      setLoading(false);
    }
  };

  const handleVerify = async (approved) => {
    try {
      const response = await fetch(`${API}/counsellor/verify-proof`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          proof_id: selectedProof.proof_id,
          approved,
          reviewer_notes: reviewerNotes
        })
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

  const displayProofs = viewMode === 'pending' ? pendingProofs : allProofs;

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button onClick={() => navigate('/counsellor-dashboard')} variant="outline" className="rounded-full">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>
            <h1 className="text-2xl font-bold text-slate-900">Class Verifications</h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-3 mb-6">
          <Button
            onClick={() => setViewMode('pending')}
            className={`rounded-full ${viewMode === 'pending' ? 'bg-amber-500 text-white' : 'bg-white text-slate-700 border-2 border-slate-200'}`}
            data-testid="pending-proofs-tab"
          >
            <Clock className="w-4 h-4 mr-2" /> Pending ({pendingProofs.length})
          </Button>
          <Button
            onClick={() => setViewMode('all')}
            className={`rounded-full ${viewMode === 'all' ? 'bg-sky-500 text-white' : 'bg-white text-slate-700 border-2 border-slate-200'}`}
            data-testid="all-proofs-tab"
          >
            <FileText className="w-4 h-4 mr-2" /> All Proofs ({allProofs.length})
          </Button>
        </div>

        {displayProofs.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <p className="text-slate-600">{viewMode === 'pending' ? 'No pending proofs to verify' : 'No proofs submitted yet'}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {displayProofs.map(proof => (
              <div
                key={proof.proof_id}
                className="bg-white rounded-2xl border-2 border-slate-200 p-6 cursor-pointer hover:shadow-lg transition-all"
                onClick={() => { setSelectedProof(proof); setShowDetailDialog(true); }}
                data-testid={`proof-card-${proof.proof_id}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-bold text-slate-900">{proof.class_title}</h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    proof.status === 'pending' ? 'bg-amber-100 text-amber-800' :
                    proof.status === 'verified' ? 'bg-emerald-100 text-emerald-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {proof.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-1">Teacher: {proof.teacher_name}</p>
                <p className="text-sm text-slate-500 mb-2">Performance: {proof.student_performance}</p>
                <p className="text-xs text-slate-400">{new Date(proof.submitted_at).toLocaleDateString()}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Proof Details</DialogTitle>
          </DialogHeader>
          {selectedProof && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="text-sm text-slate-600 mb-1">Class</p>
                <p className="font-bold text-slate-900">{selectedProof.class_title}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Teacher</p>
                  <p className="font-semibold text-slate-900">{selectedProof.teacher_name}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Performance</p>
                  <p className="font-semibold text-slate-900 capitalize">{selectedProof.student_performance}</p>
                </div>
              </div>
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="text-sm text-slate-600 mb-1">Topics Covered</p>
                <p className="text-slate-900">{selectedProof.topics_covered}</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="text-sm text-slate-600 mb-1">Feedback</p>
                <p className="text-slate-900">{selectedProof.feedback_text}</p>
              </div>
              {selectedProof.screenshot_base64 && (
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-2"><Image className="w-4 h-4 inline mr-1" /> Screenshot</p>
                  <img src={selectedProof.screenshot_base64} alt="Class proof" className="rounded-lg max-h-60 w-full object-contain" />
                </div>
              )}

              {selectedProof.status === 'pending' && (
                <div className="space-y-3 pt-2">
                  <div>
                    <Label>Reviewer Notes (optional)</Label>
                    <textarea
                      value={reviewerNotes}
                      onChange={e => setReviewerNotes(e.target.value)}
                      className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 mt-1"
                      rows={3}
                      placeholder="Add notes..."
                      data-testid="reviewer-notes-input"
                    />
                  </div>
                  <div className="flex gap-3">
                    <Button
                      onClick={() => handleVerify(true)}
                      className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-5 font-bold"
                      data-testid="approve-proof-button"
                    >
                      <CheckCircle className="w-5 h-5 mr-2" /> Approve & Credit Teacher
                    </Button>
                    <Button
                      onClick={() => handleVerify(false)}
                      variant="outline"
                      className="flex-1 border-2 border-red-200 text-red-600 hover:bg-red-50 rounded-full py-5 font-bold"
                      data-testid="reject-proof-button"
                    >
                      <XCircle className="w-5 h-5 mr-2" /> Reject
                    </Button>
                  </div>
                </div>
              )}

              {selectedProof.status !== 'pending' && selectedProof.reviewer_notes && (
                <div className="bg-amber-50 rounded-xl p-4 border-2 border-amber-200">
                  <p className="text-sm text-amber-800 font-semibold mb-1">Reviewer Notes</p>
                  <p className="text-amber-900">{selectedProof.reviewer_notes}</p>
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
