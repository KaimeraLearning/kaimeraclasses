import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, ArrowLeft, CreditCard, Users, Check, IndianRupee, Loader2 } from 'lucide-react';
import { getApiError, API } from '../utils/api';

const CREDIT_PACKAGES = [
  { id: 'pack_2000', credits: 2, price: 2000, label: '2,000' },
  { id: 'pack_5000', credits: 5000, price: 5000, label: '5,000', popular: true },
  { id: 'pack_10000', credits: 10000, price: 10000, label: '10,000' },
];

const BrowseClasses = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState([]);
  const [userCredits, setUserCredits] = useState(0);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [clsRes, meRes] = await Promise.all([
          fetch(`${API}/student/my-classes`, { credentials: 'include' }),
          fetch(`${API}/auth/me`, { credentials: 'include' })
        ]);
        if (clsRes.ok) setClasses(await clsRes.json());
        if (meRes.ok) { const me = await meRes.json(); setUserCredits(me.credits || 0); }
      } catch {}
      setLoading(false);
    };
    fetchData();
  }, []);

  const loadRazorpayScript = () => {
    return new Promise((resolve, reject) => {
      if (window.Razorpay) { resolve(window.Razorpay); return; }
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve(window.Razorpay);
      script.onerror = () => reject(new Error('Failed to load payment gateway'));
      document.head.appendChild(script);
    });
  };

  const handlePurchaseCredits = async (pkg) => {
    setIsProcessing(true);
    try {
      const res = await fetch(`${API}/payments/recharge`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_id: pkg.id })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();

      const RazorpayClass = await loadRazorpayScript();
      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        order_id: data.order_id,
        name: 'Kaimera Learning',
        description: `Recharge ${pkg.label} Credits`,
        prefill: { name: data.student_name, email: data.student_email },
        handler: async (response) => {
          try {
            const verifyRes = await fetch(`${API}/payments/verify-recharge`, {
              method: 'POST', credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature
              })
            });
            if (!verifyRes.ok) throw new Error(await getApiError(verifyRes));
            const result = await verifyRes.json();
            toast.success(result.message);
            setUserCredits(prev => prev + (result.credits_added || 0));
            setShowPaymentDialog(false);
          } catch (err) { toast.error('Verification failed: ' + err.message); }
        },
        theme: { color: '#0ea5e9' }
      };
      const rzp = new RazorpayClass(options);
      rzp.open();
    } catch (err) { toast.error(err.message); }
    finally { setIsProcessing(false); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button onClick={() => navigate('/student-dashboard')} variant="outline" className="rounded-full" data-testid="back-button">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <h1 className="text-2xl font-bold text-slate-900">My Classes</h1>
            </div>
            <div className="flex items-center gap-3 bg-sky-100 px-4 py-2 rounded-full">
              <IndianRupee className="w-5 h-5 text-sky-600" />
              <span className="font-bold text-sky-900" data-testid="header-credits-balance">{userCredits.toLocaleString()} Credits</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Button onClick={() => setShowPaymentDialog(true)} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full px-6 py-3 font-bold" data-testid="open-payment-dialog-button">
            <IndianRupee className="w-4 h-4 mr-2" /> Recharge Credits
          </Button>
        </div>

        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <GraduationCap className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-600 text-lg">No classes available. Your teacher will create classes for you.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classes.map((cls) => (
              <div key={cls.class_id} className="bg-white rounded-3xl border-2 border-slate-100 p-6 hover:shadow-lg transition-all" data-testid={`class-card-${cls.class_id}`}>
                <div className="flex gap-2 mb-4">
                  <span className="bg-sky-100 text-sky-800 px-3 py-1 rounded-full text-xs font-semibold">{cls.subject}</span>
                  <span className="bg-slate-100 text-slate-600 px-3 py-1 rounded-full text-xs">{cls.class_type}</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">{cls.title}</h3>
                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-slate-600">
                    <span className="text-sm">{cls.date} | {cls.start_time} - {cls.end_time}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Users className="w-4 h-4" />
                    <span className="text-sm">{cls.duration_days} day program</span>
                  </div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                  <p className="text-emerald-700 font-semibold text-sm">Auto-enrolled in this class</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recharge Dialog */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Recharge Credits</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            {CREDIT_PACKAGES.map((pkg) => (
              <div key={pkg.id} className={`relative bg-white rounded-2xl border-2 p-6 transition-all cursor-pointer ${
                selectedPackage?.id === pkg.id ? 'border-sky-500 shadow-lg' : 'border-slate-200 hover:border-sky-300'
              } ${pkg.popular ? 'ring-2 ring-amber-400' : ''}`}
                onClick={() => setSelectedPackage(pkg)} data-testid={`credit-package-${pkg.id}`}>
                {pkg.popular && <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 px-3 py-1 rounded-full text-xs font-bold">POPULAR</div>}
                <div className="text-center">
                  <p className="text-3xl font-bold text-slate-900 mb-1">{pkg.label}</p>
                  <p className="text-sm text-slate-600 mb-3">Credits</p>
                  <p className="text-2xl font-bold text-sky-600 flex items-center justify-center"><IndianRupee className="w-5 h-5" />{pkg.price.toLocaleString()}</p>
                </div>
                {selectedPackage?.id === pkg.id && <div className="absolute top-3 right-3"><div className="bg-sky-500 rounded-full p-1"><Check className="w-4 h-4 text-white" /></div></div>}
              </div>
            ))}
          </div>
          <Button onClick={() => selectedPackage && handlePurchaseCredits(selectedPackage)} disabled={!selectedPackage || isProcessing}
            className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg mt-4" data-testid="proceed-to-payment-button">
            {isProcessing ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Processing...</> : 'Proceed to Payment'}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BrowseClasses;
