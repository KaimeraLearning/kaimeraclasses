import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { GraduationCap, Mail, Lock, User, ShieldCheck, ArrowLeft, Check } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Login = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  
  // Login
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  
  // Register - OTP Flow
  const [regStep, setRegStep] = useState('email'); // email -> otp -> details
  const [regEmail, setRegEmail] = useState('');
  const [regOtp, setRegOtp] = useState('');
  const [regName, setRegName] = useState('');
  const [regPassword, setRegPassword] = useState('');

  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + '/student-dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ email: loginEmail, password: loginPassword })
      });
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail || 'Login failed'); }
      const data = await response.json();
      toast.success(`Welcome back, ${data.user.name}!`);
      const routes = { student: '/student-dashboard', teacher: '/teacher-dashboard', counsellor: '/counsellor-dashboard', admin: '/admin-dashboard' };
      navigate(routes[data.user.role] || '/login', { state: { user: data.user } });
    } catch (error) { toast.error(error.message); }
    finally { setIsLoading(false); }
  };

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!regEmail) { toast.error('Enter your email'); return; }
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/auth/send-otp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: regEmail })
      });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed'); }
      toast.success('OTP sent! Check your email inbox.');
      setRegStep('otp');
    } catch (error) { toast.error(error.message); }
    finally { setIsLoading(false); }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!regOtp) { toast.error('Enter the OTP'); return; }
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/auth/verify-otp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: regEmail, otp: regOtp })
      });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Invalid OTP'); }
      toast.success('Email verified!');
      setRegStep('details');
    } catch (error) { toast.error(error.message); }
    finally { setIsLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regName || !regPassword) { toast.error('Name and password required'); return; }
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: regName, email: regEmail, password: regPassword, role: 'student' })
      });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Registration failed'); }
      const data = await res.json();
      toast.success(data.message);
      navigate('/student-dashboard', { state: { user: data.user } });
    } catch (error) { toast.error(error.message); }
    finally { setIsLoading(false); }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-sky-400 to-violet-500 p-12 items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMzLjMxNCAwIDYgMi42ODYgNiA2cy0yLjY4NiA2LTYgNi02LTIuNjg2LTYtNiAyLjY4Ni02IDYtNiIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIiIG9wYWNpdHk9Ii4xIi8+PC9nPjwvc3ZnPg==')] opacity-20" />
        <div className="relative z-10 text-center max-w-md">
          <GraduationCap className="w-24 h-24 text-white mx-auto mb-6" strokeWidth={1.5} />
          <h1 className="text-5xl font-bold text-white mb-4">Kaimera Learning</h1>
          <p className="text-xl text-white/90 leading-relaxed">Connect with expert teachers, book engaging classes, and unlock your learning potential</p>
          <div className="mt-12 flex gap-8 justify-center text-white/80">
            <div className="text-center"><div className="text-3xl font-bold text-white">500+</div><div className="text-sm">Classes</div></div>
            <div className="text-center"><div className="text-3xl font-bold text-white">100+</div><div className="text-sm">Teachers</div></div>
            <div className="text-center"><div className="text-3xl font-bold text-white">2K+</div><div className="text-sm">Students</div></div>
          </div>
        </div>
      </div>

      {/* Right side */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <GraduationCap className="w-16 h-16 text-sky-500 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-slate-900">Kaimera Learning</h2>
          </div>

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-8">
              <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
              <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
            </TabsList>

            {/* Login Tab */}
            <TabsContent value="login">
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 shadow-lg">
                <h3 className="text-2xl font-bold text-slate-900 mb-2">Welcome Back!</h3>
                <p className="text-slate-600 mb-6">Sign in to continue your learning journey</p>

                <Button onClick={handleGoogleLogin} className="w-full bg-white text-slate-900 border-2 border-slate-200 hover:bg-slate-50 rounded-full py-6 font-semibold mb-6" data-testid="google-login-button">
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Continue with Google
                </Button>

                <div className="relative mb-6">
                  <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
                  <div className="relative flex justify-center text-sm"><span className="px-4 bg-white text-slate-500">Or continue with email</span></div>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <Label className="text-slate-700 font-medium mb-2 block">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <Input type="email" placeholder="you@example.com" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12" required data-testid="login-email-input" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-slate-700 font-medium mb-2 block">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <Input type="password" placeholder="••••••••" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12" required data-testid="login-password-input" />
                    </div>
                  </div>
                  <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg shadow-[0_4px_14px_0_rgba(14,165,233,0.39)] hover:-translate-y-0.5 active:translate-y-0 transition-all" disabled={isLoading} data-testid="login-submit-button">
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </div>
            </TabsContent>

            {/* Register Tab — OTP Flow */}
            <TabsContent value="register">
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 shadow-lg">
                <h3 className="text-2xl font-bold text-slate-900 mb-2">Create Account</h3>
                <p className="text-slate-600 mb-6">
                  {regStep === 'email' && 'Verify your email to get started'}
                  {regStep === 'otp' && `Enter the 6-digit code sent to ${regEmail}`}
                  {regStep === 'details' && 'Almost there! Set your name and password'}
                </p>

                {/* Step indicator */}
                <div className="flex items-center gap-2 mb-6">
                  {['email', 'otp', 'details'].map((step, i) => (
                    <div key={step} className="flex items-center gap-2 flex-1">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${regStep === step ? 'bg-sky-500 text-white' : i < ['email', 'otp', 'details'].indexOf(regStep) ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500'}`}>{i < ['email', 'otp', 'details'].indexOf(regStep) ? <Check className="w-4 h-4" /> : i + 1}</div>
                      {i < 2 && <div className={`flex-1 h-0.5 ${i < ['email', 'otp', 'details'].indexOf(regStep) ? 'bg-emerald-500' : 'bg-slate-200'}`} />}
                    </div>
                  ))}
                </div>

                {/* Step 1: Email */}
                {regStep === 'email' && (
                  <form onSubmit={handleSendOtp} className="space-y-4">
                    <div>
                      <Label className="text-slate-700 font-medium mb-2 block">Email Address</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <Input type="email" placeholder="you@example.com" value={regEmail} onChange={e => setRegEmail(e.target.value)} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12" required data-testid="register-email-input" />
                      </div>
                    </div>
                    <Button type="submit" className="w-full bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full py-6 font-bold text-lg" disabled={isLoading} data-testid="send-otp-button">
                      {isLoading ? 'Sending...' : 'Send Verification Code'}
                    </Button>
                    <p className="text-xs text-slate-500 text-center">Only students can self-register. Staff accounts are created by admin.</p>
                  </form>
                )}

                {/* Step 2: OTP */}
                {regStep === 'otp' && (
                  <form onSubmit={handleVerifyOtp} className="space-y-4">
                    <div>
                      <Label className="text-slate-700 font-medium mb-2 block">Verification Code</Label>
                      <div className="relative">
                        <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <Input type="text" placeholder="123456" value={regOtp} onChange={e => setRegOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12 text-center text-2xl tracking-widest font-bold" maxLength={6} required data-testid="otp-input" />
                      </div>
                    </div>
                    <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg" disabled={isLoading} data-testid="verify-otp-button">
                      {isLoading ? 'Verifying...' : 'Verify Email'}
                    </Button>
                    <div className="flex items-center justify-between">
                      <button type="button" onClick={() => setRegStep('email')} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"><ArrowLeft className="w-3 h-3" /> Change email</button>
                      <button type="button" onClick={handleSendOtp} className="text-sm text-sky-500 hover:text-sky-700 font-medium">Resend code</button>
                    </div>
                  </form>
                )}

                {/* Step 3: Details */}
                {regStep === 'details' && (
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="bg-emerald-50 rounded-xl p-3 flex items-center gap-2 border border-emerald-200">
                      <ShieldCheck className="w-5 h-5 text-emerald-600" />
                      <span className="text-sm text-emerald-800 font-medium">{regEmail} verified</span>
                    </div>
                    <div>
                      <Label className="text-slate-700 font-medium mb-2 block">Full Name</Label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <Input type="text" placeholder="Your full name" value={regName} onChange={e => setRegName(e.target.value)} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12" required data-testid="register-name-input" />
                      </div>
                    </div>
                    <div>
                      <Label className="text-slate-700 font-medium mb-2 block">Password</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <Input type="password" placeholder="••••••••" value={regPassword} onChange={e => setRegPassword(e.target.value)} className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-12" required data-testid="register-password-input" />
                      </div>
                    </div>
                    <Button type="submit" className="w-full bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full py-6 font-bold text-lg" disabled={isLoading} data-testid="register-submit-button">
                      {isLoading ? 'Creating...' : 'Create Student Account'}
                    </Button>
                  </form>
                )}
              </div>
            </TabsContent>
          </Tabs>

          <div className="mt-6 text-center">
            <p className="text-sm text-slate-500 mb-2">Want to try before you sign up?</p>
            <Button onClick={() => navigate('/book-demo')} variant="outline" className="rounded-full border-2 border-sky-200 text-sky-600 hover:bg-sky-50 font-semibold px-6" data-testid="book-demo-cta">Book a Free Demo Class</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
