import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { GraduationCap, Mail, Lock, User, Phone, MapPin, BookOpen, ArrowLeft, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';

import { API, getApiError } from '../utils/api';
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

const Login = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState('login'); // login, register, otp, verify-account
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', name: '', phone: '', institute: '', goal: '', preferred_time_slot: '', state: '', city: '', country: '', grade: '' });
  const [otp, setOtp] = useState('');
  const [verifyEmail, setVerifyEmail] = useState('');

  const redirectByRole = (role) => {
    const routes = { admin: '/admin-dashboard', teacher: '/teacher-dashboard', student: '/student-dashboard', counsellor: '/counsellor-dashboard' };
    navigate(routes[role] || '/login');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, password: form.password })
      });
      let data;
      try {
        data = await res.json();
      } catch {
        if (res.status === 401) throw new Error('Invalid email or password');
        if (res.status === 403) throw new Error('Account suspended or not verified');
        if (res.status === 429) throw new Error('Too many login attempts. Please wait and try again.');
        throw new Error(`Login failed. Please try again.`);
      }
      if (!res.ok) {
        throw new Error(data.detail || 'Invalid email or password');
      }

      if (data.needs_verification) {
        setVerifyEmail(data.email);
        setMode('verify-account');
        toast.info('Account not verified. Enter OTP.');
        return;
      }

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

    // Load GIS script on demand
    const loadAndInit = () => {
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
    };

    const initGoogle = () => {
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            try {
              const res = await fetch(`${API}/auth/google`, {
                method: 'POST', credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: response.credential })
              });
              let data;
              try { data = await res.json(); } catch { throw new Error('Google login failed. Please try again.'); }
              if (!res.ok) throw new Error(data.detail || 'Google login failed');
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
            // Fallback: render button in a hidden container, then click it
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
      } catch (err) {
        toast.error('Google Sign-In initialization failed');
        setLoading(false);
      }
    };

    loadAndInit();
  }, [navigate]);

  const handleSendOtp = async () => {
    if (!form.email) { toast.error('Enter your email first'); return; }
    const domain = form.email.toLowerCase().split('@').pop();
    if (!['gmail.com', 'kaimeralearning.com'].includes(domain)) { toast.error('Only @gmail.com and @kaimeralearning.com addresses are allowed'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/send-otp`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email.trim().toLowerCase() })
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Failed to send OTP. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');
      toast.success(data.message);
      setMode('otp');
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleVerifyOtp = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/verify-otp`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, otp })
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Verification failed. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'OTP verification failed');
      toast.success('Email verified! Complete your registration.');
      setMode('register-details');
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!form.name || !form.password) { toast.error('Name and password are required'); return; }
    if (form.password.length < 6) { toast.error('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, role: 'student' })
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Registration failed. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'Registration failed');

      localStorage.setItem('token', data.session_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success(data.message || 'Account created!');
      redirectByRole(data.user.role);
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleVerifyAccount = async () => {
    if (!otp) { toast.error('Enter OTP'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/verify-account`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail, otp })
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Verification failed. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'Verification failed');

      localStorage.setItem('token', data.session_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success(data.message || 'Account verified!');
      redirectByRole(data.user.role);
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleResendVerification = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/resend-verification-otp`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail })
      });
      let data;
      try { data = await res.json(); } catch { throw new Error('Failed to resend. Please try again.'); }
      if (!res.ok) throw new Error(data.detail || 'Failed');
      toast.success(data.message);
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

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

          {/* ── Login Mode ── */}
          {mode === 'login' && (
            <>
              <h2 className="text-xl font-bold text-white mb-6 text-center" data-testid="login-heading">Welcome Back</h2>
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

              <p className="text-center text-white/60 text-xs mt-6">
                New student?{' '}
                <button onClick={() => setMode('register')} className="text-sky-400 hover:text-sky-300 font-semibold" data-testid="register-link">Create Account</button>
              </p>
            </>
          )}

          {/* ── Register Step 1: Email + OTP ── */}
          {mode === 'register' && (
            <>
              <button onClick={() => setMode('login')} className="text-white/60 hover:text-white text-xs flex items-center gap-1 mb-4"><ArrowLeft className="w-3 h-3" /> Back to Login</button>
              <h2 className="text-xl font-bold text-white mb-2 text-center">Create Student Account</h2>
              <p className="text-white/50 text-xs text-center mb-6">Step 1: Verify your email</p>
              <div className="space-y-4">
                <div>
                  <Label className="text-white/80 text-xs mb-1.5 block">Email (@gmail.com only)</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} type="email" placeholder="your@gmail.com" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="register-email" />
                  </div>
                </div>
                <Button onClick={handleSendOtp} disabled={loading} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-xl font-bold h-11" data-testid="send-otp-btn">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ShieldCheck className="w-4 h-4 mr-2" /> Send Verification OTP</>}
                </Button>
              </div>
            </>
          )}

          {/* ── Register Step 2: Enter OTP ── */}
          {mode === 'otp' && (
            <>
              <button onClick={() => setMode('register')} className="text-white/60 hover:text-white text-xs flex items-center gap-1 mb-4"><ArrowLeft className="w-3 h-3" /> Back</button>
              <h2 className="text-xl font-bold text-white mb-2 text-center">Verify Email</h2>
              <p className="text-white/50 text-xs text-center mb-6">OTP sent to {form.email}</p>
              <div className="space-y-4">
                <Input value={otp} onChange={e => setOtp(e.target.value)} placeholder="Enter 6-digit OTP" className="bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl text-center text-2xl tracking-[0.5em] font-bold" maxLength={6} data-testid="otp-input" />
                <Button onClick={handleVerifyOtp} disabled={loading} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-bold h-11" data-testid="verify-otp-btn">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ArrowRight className="w-4 h-4 mr-2" /> Verify & Continue</>}
                </Button>
              </div>
            </>
          )}

          {/* ── Register Step 3: Profile Details ── */}
          {mode === 'register-details' && (
            <>
              <button onClick={() => setMode('register')} className="text-white/60 hover:text-white text-xs flex items-center gap-1 mb-4"><ArrowLeft className="w-3 h-3" /> Back</button>
              <h2 className="text-xl font-bold text-white mb-2 text-center">Complete Your Profile</h2>
              <p className="text-white/50 text-xs text-center mb-6">{form.email} (verified)</p>
              <form onSubmit={handleRegister} className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
                <div>
                  <Label className="text-white/80 text-xs mb-1 block">Full Name *</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Full name" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" required data-testid="register-name" />
                  </div>
                </div>
                <div>
                  <Label className="text-white/80 text-xs mb-1 block">Password *</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} type="password" placeholder="Min 6 characters" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" required data-testid="register-password" />
                  </div>
                </div>
                <div>
                  <Label className="text-white/80 text-xs mb-1 block">Phone</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="Phone number" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" data-testid="register-phone" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-white/80 text-xs mb-1 block">City</Label>
                    <Input value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} placeholder="City" className="bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/80 text-xs mb-1 block">State</Label>
                    <Input value={form.state} onChange={e => setForm({ ...form, state: e.target.value })} placeholder="State" className="bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl text-sm" />
                  </div>
                </div>
                <div>
                  <Label className="text-white/80 text-xs mb-1 block">Institute</Label>
                  <div className="relative">
                    <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={form.institute} onChange={e => setForm({ ...form, institute: e.target.value })} placeholder="School/College" className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" />
                  </div>
                </div>
                <div>
                  <Label className="text-white/80 text-xs mb-1 block">Grade/Year</Label>
                  <Input value={form.grade} onChange={e => setForm({ ...form, grade: e.target.value })} placeholder="e.g. Grade 10, Year 2" className="bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl" />
                </div>
                <Button type="submit" disabled={loading} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-xl font-bold h-11 mt-2" data-testid="register-submit">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Account'}
                </Button>
              </form>
            </>
          )}

          {/* ── Account Verification (for manually created users) ── */}
          {mode === 'verify-account' && (
            <>
              <button onClick={() => { setMode('login'); setOtp(''); }} className="text-white/60 hover:text-white text-xs flex items-center gap-1 mb-4"><ArrowLeft className="w-3 h-3" /> Back to Login</button>
              <h2 className="text-xl font-bold text-white mb-2 text-center">Verify Your Account</h2>
              <p className="text-white/50 text-xs text-center mb-6">Enter the OTP sent to <span className="text-sky-400">{verifyEmail}</span></p>
              <div className="space-y-4">
                <Input value={otp} onChange={e => setOtp(e.target.value)} placeholder="Enter 6-digit OTP" className="bg-white/10 border-white/20 text-white placeholder:text-white/40 rounded-xl text-center text-2xl tracking-[0.5em] font-bold" maxLength={6} data-testid="verify-account-otp" />
                <Button onClick={handleVerifyAccount} disabled={loading} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-bold h-11" data-testid="verify-account-btn">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ShieldCheck className="w-4 h-4 mr-2" /> Verify & Sign In</>}
                </Button>
                <Button onClick={handleResendVerification} variant="ghost" disabled={loading} className="w-full text-white/60 hover:text-white text-xs" data-testid="resend-otp-btn">
                  Resend OTP
                </Button>
              </div>
            </>
          )}

        </div>

        <p className="text-center text-white/30 text-xs mt-6">Kaimera Learning &copy; {new Date().getFullYear()}</p>
      </div>
    </div>
  );
};

export default Login;
