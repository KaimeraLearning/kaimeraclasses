import { getApiError } from '../utils/api';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, Star, Send, Loader2, CheckCircle2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DemoFeedback = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [demos, setDemos] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(null);
  const [feedbackForms, setFeedbackForms] = useState({});

  const fetchData = useCallback(async () => {
    try {
      const [userRes, demosRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/demo/my-demos`, { credentials: 'include' })
      ]);
      if (!userRes.ok) { navigate('/login'); return; }
      const userData = await userRes.json();
      setUser(userData);

      if (demosRes.ok) {
        const allDemos = await demosRes.json();
        // Show demos that are accepted (class completed) but no feedback yet
        const completedDemos = allDemos.filter(d => d.status === 'accepted' && !d.feedback_id);
        setDemos(completedDemos);

        // Get unique teacher names for selection
        const uniqueTeachers = [...new Set(allDemos.filter(d => d.accepted_by_teacher_id).map(d => JSON.stringify({ id: d.accepted_by_teacher_id, name: d.accepted_by_teacher_name })))].map(JSON.parse);
        setTeachers(uniqueTeachers);
      }
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSubmit = async (demoId) => {
    const form = feedbackForms[demoId];
    if (!form?.rating) { toast.error('Please select a rating'); return; }
    if (!form?.feedback_text?.trim()) { toast.error('Please write some feedback'); return; }

    setSubmitting(demoId);
    try {
      const res = await fetch(`${API}/demo/feedback`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          demo_id: demoId,
          rating: form.rating,
          feedback_text: form.feedback_text,
          preferred_teacher_id: form.preferred_teacher_id || null
        })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Feedback submitted! A counselor will assign you a regular teacher soon.');
      fetchData();
    } catch (err) { toast.error(err.message); }
    finally { setSubmitting(null); }
  };

  const updateForm = (demoId, field, value) => {
    setFeedbackForms(prev => ({
      ...prev,
      [demoId]: { ...(prev[demoId] || {}), [field]: value }
    }));
  };

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50">
      {/* Header */}
      <div className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate('/student-dashboard')} className="rounded-full" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>Demo Feedback</h1>
            <p className="text-xs text-slate-500">Rate your demo and choose your preferred teacher</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {demos.length === 0 ? (
          <div className="text-center py-16">
            <CheckCircle2 className="w-16 h-16 text-emerald-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-600 mb-2">All Caught Up!</h3>
            <p className="text-slate-400">No pending demo feedback. Check back after your next demo session.</p>
            <Button onClick={() => navigate('/student-dashboard')} className="mt-6 bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="go-dashboard-btn">
              Back to Dashboard
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {demos.map(demo => {
              const form = feedbackForms[demo.demo_id] || {};
              return (
                <div key={demo.demo_id} className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8" data-testid={`feedback-card-${demo.demo_id}`}>
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">Demo with {demo.accepted_by_teacher_name}</h3>
                      <p className="text-sm text-slate-500">{demo.preferred_date} at {demo.preferred_time_slot}</p>
                    </div>
                    <span className="bg-sky-100 text-sky-700 text-xs font-medium px-3 py-1 rounded-full">Demo #{demo.demo_number}</span>
                  </div>

                  {/* Rating */}
                  <div className="mb-5">
                    <label className="text-sm font-medium text-slate-700 block mb-2">How was your experience? *</label>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map(star => (
                        <button
                          key={star}
                          onClick={() => updateForm(demo.demo_id, 'rating', star)}
                          className="transition-transform hover:scale-110"
                          data-testid={`rating-${demo.demo_id}-${star}`}
                        >
                          <Star
                            className={`w-8 h-8 ${(form.rating || 0) >= star ? 'text-amber-400 fill-amber-400' : 'text-slate-200'}`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Feedback text */}
                  <div className="mb-5">
                    <label className="text-sm font-medium text-slate-700 block mb-2">Your feedback *</label>
                    <textarea
                      placeholder="Tell us about your experience..."
                      value={form.feedback_text || ''}
                      onChange={e => updateForm(demo.demo_id, 'feedback_text', e.target.value)}
                      className="w-full bg-slate-50 border-2 border-slate-200 rounded-xl px-4 py-3 text-sm resize-none h-24 focus:outline-none focus:ring-4 focus:ring-sky-500/20 focus:border-sky-500 transition-all"
                      data-testid={`feedback-text-${demo.demo_id}`}
                    />
                  </div>

                  {/* Preferred teacher */}
                  <div className="mb-6">
                    <label className="text-sm font-medium text-slate-700 block mb-2">Preferred teacher for regular classes</label>
                    <select
                      value={form.preferred_teacher_id || ''}
                      onChange={e => updateForm(demo.demo_id, 'preferred_teacher_id', e.target.value)}
                      className="w-full bg-slate-50 border-2 border-slate-200 rounded-xl h-11 px-4 text-sm"
                      data-testid={`preferred-teacher-${demo.demo_id}`}
                    >
                      <option value="">No preference / Let counselor decide</option>
                      {teachers.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>

                  <Button
                    onClick={() => handleSubmit(demo.demo_id)}
                    disabled={submitting === demo.demo_id}
                    className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-5 font-bold shadow-[0_4px_14px_0_rgba(14,165,233,0.39)]"
                    data-testid={`submit-feedback-${demo.demo_id}`}
                  >
                    {submitting === demo.demo_id ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Send className="w-4 h-4 mr-2" />
                    )}
                    Submit Feedback
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default DemoFeedback;
