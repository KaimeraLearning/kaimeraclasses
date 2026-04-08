import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, ArrowLeft, Calendar, Clock, Users, CreditCard, Check } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CREDIT_PACKAGES = [
  { id: 'small', credits: 10, price: 10, popular: false },
  { id: 'medium', credits: 25, price: 20, popular: true },
  { id: 'large', credits: 50, price: 35, popular: false }
];

const BrowseClasses = () => {
  const navigate = useNavigate();
  const [classes, setClasses] = useState([]);
  const [userCredits, setUserCredits] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [userRes, classesRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/classes/browse`, { credentials: 'include' })
      ]);

      if (!userRes.ok || !classesRes.ok) throw new Error('Failed to fetch data');

      const userData = await userRes.json();
      const classesData = await classesRes.json();

      setUserCredits(userData.credits);
      setClasses(classesData);
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load classes');
      setLoading(false);
    }
  };

  const handleBookClass = async (cls) => {
    if (userCredits < cls.credits_required) {
      setShowPaymentDialog(true);
      return;
    }

    try {
      const response = await fetch(`${API}/classes/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ class_id: cls.class_id })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      const data = await response.json();
      toast.success('Class booked successfully!');
      setUserCredits(data.credits_remaining);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handlePurchaseCredits = async (pkg) => {
    setIsProcessing(true);
    try {
      const originUrl = window.location.origin;
      const response = await fetch(`${API}/payments/checkout?package_id=${pkg.id}&origin_url=${encodeURIComponent(originUrl)}`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
      }

      const data = await response.json();
      window.location.href = data.url;
    } catch (error) {
      toast.error(error.message);
      setIsProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Loading classes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => navigate('/student-dashboard')}
                variant="outline"
                className="rounded-full"
                data-testid="back-button"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <h1 className="text-2xl font-bold text-slate-900">Browse Classes</h1>
            </div>
            <div className="flex items-center gap-3 bg-sky-100 px-4 py-2 rounded-full">
              <CreditCard className="w-5 h-5 text-sky-600" />
              <span className="font-bold text-sky-900" data-testid="header-credits-balance">{userCredits} Credits</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Button
            onClick={() => setShowPaymentDialog(true)}
            className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full px-6 py-3 font-bold"
            data-testid="open-payment-dialog-button"
          >
            <CreditCard className="w-4 h-4 mr-2" />
            Purchase Credits
          </Button>
        </div>

        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <GraduationCap className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-600 text-lg">No classes available at the moment.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classes.map((cls) => (
              <div
                key={cls.class_id}
                className="bg-white rounded-3xl border-2 border-slate-200 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] hover:-translate-y-1 hover:shadow-[4px_6px_0px_0px_rgba(203,213,225,1)] transition-all overflow-hidden"
                data-testid={`class-card-${cls.class_id}`}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">
                      {cls.subject}
                    </span>
                    <span className="bg-sky-100 text-sky-800 px-3 py-1 rounded-full text-xs font-semibold">
                      {cls.class_type}
                    </span>
                  </div>

                  <h3 className="text-xl font-bold text-slate-900 mb-2">{cls.title}</h3>
                  <p className="text-sm text-slate-600 mb-4">by {cls.teacher_name}</p>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-slate-600">
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm">{format(parseISO(cls.date), 'MMM dd, yyyy')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-600">
                      <Clock className="w-4 h-4" />
                      <span className="text-sm">{cls.start_time} - {cls.end_time}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-600">
                      <Users className="w-4 h-4" />
                      <span className="text-sm">{cls.enrolled_students.length} / {cls.max_students} students</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-5 h-5 text-amber-500" />
                      <span className="font-bold text-lg text-slate-900">{cls.credits_required}</span>
                      <span className="text-sm text-slate-600">credits</span>
                    </div>
                    {cls.enrolled_students.length >= cls.max_students && (
                      <span className="text-xs text-red-600 font-semibold">FULL</span>
                    )}
                  </div>

                  <Button
                    onClick={() => handleBookClass(cls)}
                    disabled={cls.enrolled_students.length >= cls.max_students}
                    className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid={`book-class-button-${cls.class_id}`}
                  >
                    {cls.enrolled_students.length >= cls.max_students ? 'Class Full' : 'Book Class'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Payment Dialog */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Purchase Credits</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            {CREDIT_PACKAGES.map((pkg) => (
              <div
                key={pkg.id}
                className={`relative bg-white rounded-2xl border-2 p-6 transition-all cursor-pointer ${
                  selectedPackage?.id === pkg.id
                    ? 'border-sky-500 shadow-lg'
                    : 'border-slate-200 hover:border-sky-300'
                } ${pkg.popular ? 'ring-2 ring-amber-400' : ''}`}
                onClick={() => setSelectedPackage(pkg)}
                data-testid={`credit-package-${pkg.id}`}
              >
                {pkg.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 px-3 py-1 rounded-full text-xs font-bold">
                    POPULAR
                  </div>
                )}
                <div className="text-center">
                  <p className="text-3xl font-bold text-slate-900 mb-1">{pkg.credits}</p>
                  <p className="text-sm text-slate-600 mb-3">Credits</p>
                  <p className="text-2xl font-bold text-sky-600">${pkg.price}</p>
                </div>
                {selectedPackage?.id === pkg.id && (
                  <div className="absolute top-3 right-3">
                    <div className="bg-sky-500 rounded-full p-1">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <Button
            onClick={() => selectedPackage && handlePurchaseCredits(selectedPackage)}
            disabled={!selectedPackage || isProcessing}
            className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg mt-4"
            data-testid="proceed-to-payment-button"
          >
            {isProcessing ? 'Processing...' : 'Proceed to Payment'}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BrowseClasses;
