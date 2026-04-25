import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { GraduationCap, Mail, Lock, User, Phone, MapPin, BookOpen, ArrowLeft, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';
import { getApiError } from '../utils/api';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

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
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      if (data.needs_verification) {
        setVerifyEmail(data.email);
        setMode('verify-account');
        toast.info('Account not verified. Please enter the OTP sent to your email.');
        return;
      }

      localStorage.setItem('token', data.session_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success(`Welcome back, ${data.user.name}!`);
      redirectByRole(data.user.role);
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleGoogleLogin = async (credentialResponse) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/google`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Google login failed');

      localStorage.setItem('token', data.session_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success(`Welcome, ${data.user.name}!`);
      redirectByRole(data.user.role);
    } catch (err) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  const handleSendOtp = async () => {
    if (!form.email) { toast.error('Enter your email first'); return; }
    if (!form.email.toLowerCase().endsWith('@gmail.com')) { toast.error('Only @gmail.com addresses are allowed'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/send-otp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email })
      });
      const data = await res.json();
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
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, otp })
      });
      const data = await res.json();
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
      const data = await res.json();
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
      const data = await res.json();
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
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail })
      });
      const data = await res.json();
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
            <div className="w-12 h-12 bg-sky-500 rounded-2xl flex items-center justify-center shadow-lg shadow-sky-500/30">
              <GraduationCap className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight">Kaimera Learning</h1>
          </div>
          <p className="text-sky-300 text-sm font-medium">Learning Management Platform</p>
        </div>

        <div className="bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 p-8 shadow-2xl">

          {/* ── Login Mode ── */}
          {mode === 'login' && (
            <>
              <h2 className="text-xl font-bold text-white mb-6 text-center" data-testid="login-heading">Sign In</h2>
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
              <div className="flex justify-center" data-testid="google-login-btn">
                <GoogleLogin
                  onSuccess={handleGoogleLogin}
                  onError={() => toast.error('Google login failed')}
                  theme="filled_black"
                  shape="pill"
                  size="large"
                  text="continue_with"
                  width="350"
                />
              </div>

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
