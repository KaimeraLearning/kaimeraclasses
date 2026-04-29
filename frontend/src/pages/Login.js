import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Mail, Lock, User, Phone, BookOpen, Calendar, Clock, MessageSquare, Loader2, Sparkles } from 'lucide-react';

import { API, getApiError , apiFetch} from '../utils/api';
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: '', password: '' });

  const [demoOpen, setDemoOpen] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demo, setDemo] = useState({
    name: '', email: '', phone: '', age: '', institute: '',
    preferred_date: '', preferred_time_slot: '', message: ''
  });

  const redirectByRole = (role) => {
    const routes = { admin: '/admin-dashboard', teacher: '/teacher-dashboard', student: '/student-dashboard', counsellor: '/counsellor-dashboard' };
    navigate(routes[role] || '/login');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiFetch(`${API}/auth/login`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, password: form.password })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      localStorage.setItem('token', data.session_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success(`Welcome back, ${data.user.name}!`);
      redirectByRole(data.user.role);
    } catch (err) {
      toast.error(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = useCallback(() => {
    if (!GOOGLE_CLIENT_ID) {
      toast.error('Google login not configured');
      return;
    }
    setLoading(true);

    const initGoogle = () => {
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            try {
              const res = await apiFetch(`${API}/auth/google`, {
                method: 'POST', credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: response.credential })
              });
              if (!res.ok) throw new Error(await getApiError(res));
              const data = await res.json();
              localStorage.setItem('token', data.session_token);
              localStorage.setItem('user', JSON.stringify(data.user));
              toast.success(`Welcome, ${data.user.name}!`);
              redirectByRole(data.user.role);
            } catch (err) {
              toast.error(err.message || 'Google login failed');
            } finally {
              setLoading(false);
            }
          }
        });
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            const container = document.getElementById('google-btn-container');
            if (container) {
              container.innerHTML = '';
              window.google.accounts.id.renderButton(container, {
                theme: 'filled_black', size: 'large', shape: 'pill', text: 'continue_with', width: 350
              });
              const btn = container.querySelector('[role="button"]') || container.querySelector('div[style]');
              if (btn) btn.click();
            }
            setLoading(false);
          }
        });
      } catch {
        toast.error('Google Sign-In initialization failed');
        setLoading(false);
      }
    };

    if (window.google?.accounts?.id) {
      initGoogle();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = initGoogle;
    script.onerror = () => { toast.error('Failed to load Google Sign-In'); setLoading(false); };
    document.head.appendChild(script);
  }, [navigate]);

  const handleBookDemo = async (e) => {
    e.preventDefault();
    if (!demo.name || !demo.email || !demo.phone || !demo.preferred_date || !demo.preferred_time_slot) {
      toast.error('Please fill name, email, phone, preferred date and time');
      return;
    }
    // Block past date+time before bothering the server
    const scheduled = new Date(`${demo.preferred_date}T${demo.preferred_time_slot}:00`);
    if (Number.isNaN(scheduled.getTime()) || scheduled <= new Date()) {
      toast.error('Please pick a future date and time. Past slots are not allowed.');
      return;
    }
    setDemoLoading(true);
    try {
      const payload = {
        name: demo.name.trim(),
        email: demo.email.trim().toLowerCase(),
        phone: demo.phone.trim(),
        age: demo.age ? parseInt(demo.age, 10) : null,
        institute: demo.institute || null,
        preferred_date: demo.preferred_date,
        preferred_time_slot: demo.preferred_time_slot,
        message: demo.message || null
      };
      const res = await apiFetch(`${API}/demo/request`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Demo booked! Our team will contact you shortly.');
      setDemoOpen(false);
      setDemo({ name: '', email: '', phone: '', age: '', institute: '', preferred_date: '', preferred_time_slot: '', message: '' });
    } catch (err) {
      toast.error(err.message || 'Failed to book demo. Please try again.');
    } finally {
      setDemoLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-3">
            <img
              src="https://static.wixstatic.com/media/3427af_c1564f2d04d34070be92706f5c62fe6c~mv2.png/v1/fill/w_186,h_194,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Kaimera%20final%20logo.png"
              alt="Logo"
              className="w-14 h-14 object-contain"
            />
            <h1 className="text-3xl font-black text-white tracking-tight">Kaimera Learning</h1>
          </div>
          <p className="text-sky-300 text-sm font-medium">Empowering the Next Generation of Speakers</p>
        </div>

        <div className="bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 p-8 shadow-2xl">

          {/* Book a Free Demo — primary CTA for new students */}
          <div className="mb-6 bg-gradient-to-r from-emerald-500/20 to-sky-500/20 border border-emerald-400/30 rounded-2xl p-4 text-center">
            <p className="text-emerald-200 text-xs font-semibold mb-2 flex items-center justify-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> NEW HERE?
            </p>
            <Button
              onClick={() => setDemoOpen(true)}
              className="w-full bg-gradient-to-r from-emerald-500 to-sky-500 hover:from-emerald-600 hover:to-sky-600 text-white rounded-xl font-bold h-11"
              data-testid="open-book-demo-btn"
            >
              Book a Free Demo
            </Button>
            <p className="text-white/60 text-[11px] mt-2">No account needed — we'll reach out!</p>
          </div>

          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/20" />
            <span className="text-white/50 text-xs">existing user</span>
            <div className="flex-1 h-px bg-white/20" />
          </div>

          <h2 className="text-lg font-bold text-white mb-4 text-center" data-testid="login-heading">Welcome Back</h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <Label className="text-white/80 text-xs mb-1.5 block">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} type="email" placeholder="your@gmail.com" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" required data-testid="login-email" />
              </div>
            </div>
            <div>
              <Label className="text-white/80 text-xs mb-1.5 block">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} type="password" placeholder="Enter password" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" required data-testid="login-password" />
              </div>
            </div>
            <Button type="submit" disabled={loading} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-xl font-bold h-11" data-testid="login-submit">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign In'}
            </Button>
          </form>

          {/* Google Login */}
          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/20" />
            <span className="text-white/50 text-xs">or</span>
            <div className="flex-1 h-px bg-white/20" />
          </div>
          <div id="google-btn-container" style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }} />
          {GOOGLE_CLIENT_ID && (
            <Button type="button" onClick={handleGoogleLogin} disabled={loading} variant="outline"
              className="w-full rounded-xl h-11 bg-white/5 border-white/20 text-white hover:bg-white/10 font-semibold" data-testid="google-login-btn">
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </Button>
          )}
        </div>

        <p className="text-center text-white/30 text-xs mt-6">Kaimera Learning &copy; {new Date().getFullYear()}</p>
      </div>

      {/* Book a Free Demo Dialog */}
      <Dialog open={demoOpen} onOpenChange={setDemoOpen}>
        <DialogContent className="max-w-md bg-slate-900 text-white border-white/10 max-h-[90vh] overflow-y-auto" data-testid="book-demo-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" /> Book Your Free Demo
            </DialogTitle>
            <DialogDescription className="text-white/60 text-sm">
              Fill the form — our counsellor will assign a teacher and contact you on phone/email shortly.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleBookDemo} className="space-y-3 mt-2">
            <div>
              <Label className="text-white/80 text-xs mb-1 block">Full Name *</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input value={demo.name} onChange={e => setDemo({ ...demo, name: e.target.value })} placeholder="Student's name" required className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-name" />
              </div>
            </div>
            <div>
              <Label className="text-white/80 text-xs mb-1 block">Email *</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input value={demo.email} onChange={e => setDemo({ ...demo, email: e.target.value })} type="email" placeholder="email@gmail.com" required className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-email" />
              </div>
            </div>
            <div>
              <Label className="text-white/80 text-xs mb-1 block">Phone (with country code) *</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input value={demo.phone} onChange={e => setDemo({ ...demo, phone: e.target.value })} placeholder="+91 9XXXXXXXXX" required className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-phone" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-white/80 text-xs mb-1 block">Age</Label>
                <Input type="number" min="3" max="80" value={demo.age} onChange={e => setDemo({ ...demo, age: e.target.value })} placeholder="14" className="bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-age" />
              </div>
              <div>
                <Label className="text-white/80 text-xs mb-1 block">School / College</Label>
                <div className="relative">
                  <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input value={demo.institute} onChange={e => setDemo({ ...demo, institute: e.target.value })} placeholder="Institute" className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-institute" />
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-white/80 text-xs mb-1 block">Preferred Date *</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input type="date" min={today} value={demo.preferred_date} onChange={e => setDemo({ ...demo, preferred_date: e.target.value })} required className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-date" />
                </div>
              </div>
              <div>
                <Label className="text-white/80 text-xs mb-1 block">Preferred Time *</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input type="time" value={demo.preferred_time_slot} onChange={e => setDemo({ ...demo, preferred_time_slot: e.target.value })} required className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-time" />
                </div>
              </div>
            </div>
            <div>
              <Label className="text-white/80 text-xs mb-1 block">Message (optional)</Label>
              <div className="relative">
                <MessageSquare className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                <Textarea value={demo.message} onChange={e => setDemo({ ...demo, message: e.target.value })} placeholder="What does the student want to learn?" rows={3} className="pl-10 bg-white/5 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="demo-message" />
              </div>
            </div>
            <Button type="submit" disabled={demoLoading} className="w-full bg-gradient-to-r from-emerald-500 to-sky-500 hover:from-emerald-600 hover:to-sky-600 text-white rounded-xl font-bold h-11 mt-2" data-testid="submit-book-demo">
              {demoLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Sparkles className="w-4 h-4 mr-2" /> Submit & Get a Call</>}
            </Button>
            <p className="text-white/40 text-[11px] text-center">By submitting, you agree to be contacted by our team.</p>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Login;
