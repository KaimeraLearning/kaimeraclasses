import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { API } from '../utils/api';

const PaymentSuccess = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('checking'); // checking, success, error
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 5;

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (!sessionId) {
      toast.error('Invalid payment session');
      navigate('/browse-classes');
      return;
    }

    pollPaymentStatus(sessionId);
  }, [searchParams, navigate]);

  const pollPaymentStatus = async (sessionId, attemptCount = 0) => {
    if (attemptCount >= maxAttempts) {
      setStatus('error');
      toast.error('Payment status check timed out. Please check your account.');
      return;
    }

    try {
      const response = await fetch(`${API}/payments/status/${sessionId}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to check payment status');
      }

      const data = await response.json();

      if (data.payment_status === 'paid') {
        setStatus('success');
        toast.success('Payment successful! Credits added to your account.');
        return;
      } else if (data.status === 'expired') {
        setStatus('error');
        toast.error('Payment session expired.');
        return;
      }

      // If still pending, poll again after 2 seconds
      setAttempts(attemptCount + 1);
      setTimeout(() => pollPaymentStatus(sessionId, attemptCount + 1), 2000);
    } catch (error) {
      console.error('Payment status check error:', error);
      setStatus('error');
      toast.error('Error checking payment status.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 max-w-md text-center shadow-lg">
        {status === 'checking' && (
          <>
            <Loader2 className="w-16 h-16 text-sky-500 mx-auto mb-4 animate-spin" />
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Processing Payment</h2>
            <p className="text-slate-600">
              Please wait while we confirm your payment...
            </p>
            <p className="text-sm text-slate-500 mt-4">
              Attempt {attempts + 1} of {maxAttempts}
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Payment Successful!</h2>
            <p className="text-slate-600 mb-6">
              Your credits have been added to your account.
            </p>
            <Button
              onClick={() => navigate('/browse-classes')}
              className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold"
              data-testid="return-to-classes-button"
            >
              Browse Classes
            </Button>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">⚠️</span>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Payment Issue</h2>
            <p className="text-slate-600 mb-6">
              There was an issue processing your payment. Please check your account or try again.
            </p>
            <Button
              onClick={() => navigate('/browse-classes')}
              className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold"
              data-testid="return-to-classes-button"
            >
              Return to Classes
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default PaymentSuccess;
