import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { GraduationCap, Send, Calendar, Clock, User, Mail, Phone, Building, ArrowLeft, CheckCircle2 } from 'lucide-react';

import { API , apiFetch} from '../utils/api';

const BookDemo = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    age: '',
    institute: '',
    preferred_date: '',
    preferred_time_slot: '',
    message: ''
  });

  // Check if user is logged in and pre-fill
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await apiFetch(`${API}/auth/me`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setForm(prev => ({
            ...prev,
            name: data.name || '',
            email: data.email || '',
            phone: data.phone || '',
            institute: data.institute || ''
          }));
        }
      } catch { /* Not logged in, that's fine */ }
    };
    checkAuth();
  }, []);

  // Set min date to today
  const today = new Date().toISOString().split('T')[0];

  const timeSlots = [
    '08:00', '09:00', '10:00', '11:00', '12:00',
    '13:00', '14:00', '15:00', '16:00', '17:00',
    '18:00', '19:00', '20:00', '21:00', '22:00', 
    '23:00', '24:00'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.phone || form.phone.length < 8) {
      toast.error('Please enter a valid phone number');
      return;
    }
    if (form.preferred_date && form.preferred_time_slot) {
      const scheduled = new Date(`${form.preferred_date}T${form.preferred_time_slot}:00`);
      if (Number.isNaN(scheduled.getTime()) || scheduled <= new Date()) {
        toast.error('Please pick a future date and time. Past slots are not allowed.');
        return;
      }
    }
    setIsLoading(true);
    try {
      const payload = {
        name: form.name,
        email: form.email,
        phone: form.phone,
        age: form.age ? parseInt(form.age) : null,
        institute: form.institute || null,
        preferred_date: form.preferred_date,
        preferred_time_slot: form.preferred_time_slot,
        message: form.message || null
      };
      const res = await apiFetch(`${API}/demo/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to submit');
      }
      setSubmitted(true);
      toast.success('Demo request submitted!');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-12 max-w-md text-center">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10 text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Fredoka, sans-serif' }}>Demo Request Submitted!</h2>
          <p className="text-slate-600 mb-2">We've received your request. A teacher will accept your demo shortly.</p>
          <p className="text-sm text-slate-500 mb-8">You'll be notified once your demo is confirmed.</p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => setSubmitted(false)} variant="outline" className="rounded-full border-2 border-slate-200 px-6" data-testid="book-another-demo-btn">
              Book Another
            </Button>
            {user ? (
              <Button onClick={() => navigate(`/${user.role === 'admin' ? 'admin' : user.role}-dashboard`)} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6" data-testid="go-dashboard-btn">
                Go to Dashboard
              </Button>
            ) : (
              <Button onClick={() => navigate('/login')} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6" data-testid="go-login-btn">
                Login / Register
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - vibrant marketing */}
      <div className="hidden lg:flex lg:w-5/12 bg-gradient-to-br from-sky-400 via-sky-500 to-violet-500 p-12 items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `radial-gradient(circle at 25% 25%, white 1px, transparent 1px), radial-gradient(circle at 75% 75%, white 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }} />
        <div className="relative z-10 text-center max-w-sm">
          <GraduationCap className="w-20 h-20 text-white mx-auto mb-6" strokeWidth={1.5} />
          <h1 className="text-4xl font-bold text-white mb-4" style={{ fontFamily: 'Fredoka, sans-serif' }}>
            Try a Free Demo Class
          </h1>
          <p className="text-lg text-white/90 leading-relaxed mb-8">
            Experience our 1-on-1 learning approach. Connect with expert teachers and see the difference.
          </p>
          <div className="space-y-4 text-left">
            {['Personalized attention from expert teachers', 'Interactive 1-on-1 video sessions', 'No commitment, just learning'].map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-white/90">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <span className="text-sm">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-gradient-to-br from-sky-50 via-white to-amber-50">
        <div className="w-full max-w-lg">
          {/* Mobile header */}
          <div className="lg:hidden text-center mb-6">
            <GraduationCap className="w-12 h-12 text-sky-500 mx-auto mb-2" />
            <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>Book a Demo</h2>
          </div>

          {/* Nav links */}
          <div className="flex items-center justify-between mb-6">
            <Button variant="ghost" onClick={() => navigate(user ? `/${user.role}-dashboard` : '/login')} className="text-slate-500 hover:text-slate-700 rounded-full px-3" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4 mr-1" /> {user ? 'Dashboard' : 'Login'}
            </Button>
            {!user && (
              <Button variant="ghost" onClick={() => navigate('/login')} className="text-sky-600 hover:text-sky-700 rounded-full px-3 text-sm" data-testid="login-link">
                Already have an account? Login
              </Button>
            )}
          </div>

          <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
            <h3 className="text-2xl font-bold text-slate-900 mb-1 hidden lg:block" style={{ fontFamily: 'Fredoka, sans-serif' }}>Book Your Demo</h3>
            <p className="text-slate-500 mb-6 text-sm hidden lg:block">Fill in the details and we'll match you with a teacher</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name & Email row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Full Name *</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      type="text" placeholder="Your name" required
                      value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                      className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                      data-testid="demo-name-input"
                    />
                  </div>
                </div>
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Email *</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      type="email" placeholder="you@example.com" required
                      value={form.email} onChange={e => setForm({...form, email: e.target.value})}
                      className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                      data-testid="demo-email-input"
                    />
                  </div>
                </div>
              </div>

              {/* Phone & Age row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Phone *</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      type="tel" placeholder="+91 98765 43210" required
                      value={form.phone} onChange={e => setForm({...form, phone: e.target.value})}
                      className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                      data-testid="demo-phone-input"
                    />
                  </div>
                </div>
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Age</Label>
                  <Input
                    type="number" placeholder="Your age" min="5" max="100"
                    value={form.age} onChange={e => setForm({...form, age: e.target.value})}
                    className="bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                    data-testid="demo-age-input"
                  />
                </div>
              </div>

              {/* Institute */}
              <div>
                <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Institute / School</Label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    type="text"
                    placeholder="Your school or institute"
                    value={form.institute}
                    onChange={e => setForm({ ...form, institute: e.target.value })}
                    className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                    data-testid="demo-institute-input"
                  />
                </div>
              </div>

              {/* Date & Time row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Preferred Date *</Label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      type="date" required min={today}
                      value={form.preferred_date} onChange={e => setForm({...form, preferred_date: e.target.value})}
                      className="pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm"
                      data-testid="demo-date-input"
                    />
                  </div>
                </div>
                <div>
                  <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Preferred Time *</Label>
                  <div className="relative">
                    <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <select
                      required
                      value={form.preferred_time_slot}
                      onChange={e => setForm({...form, preferred_time_slot: e.target.value})}
                      className="w-full pl-10 bg-slate-50 border-2 border-slate-200 rounded-xl h-11 text-sm text-slate-900 appearance-none"
                      data-testid="demo-time-select"
                    >
                      <option value="">Select time</option>
                      {timeSlots.map(t => (
                        <option key={t} value={t}>
                          {parseInt(t) < 12 ? `${t} AM` : parseInt(t) === 12 ? '12:00 PM' : `${parseInt(t) - 12}:00 PM`}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Message */}
              <div>
                <Label className="text-slate-700 font-medium text-sm mb-1.5 block">Message (optional)</Label>
                <textarea
                  placeholder="Anything you'd like us to know..."
                  value={form.message} onChange={e => setForm({...form, message: e.target.value})}
                  className="w-full bg-slate-50 border-2 border-slate-200 rounded-xl px-4 py-3 text-sm resize-none h-20 focus:outline-none focus:ring-4 focus:ring-sky-500/20 focus:border-sky-500 transition-all"
                  data-testid="demo-message-input"
                />
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-base shadow-[0_4px_14px_0_rgba(14,165,233,0.39)] hover:-translate-y-0.5 active:translate-y-0 transition-all"
                data-testid="demo-submit-btn"
              >
                {isLoading ? 'Submitting...' : (
                  <><Send className="w-4 h-4 mr-2" /> Book My Demo</>
                )}
              </Button>

              <p className="text-xs text-slate-400 text-center">
                Max 2 demo sessions per student. By booking, you agree to our terms.
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BookDemo;
