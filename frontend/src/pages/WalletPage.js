import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, IndianRupee, Download, CreditCard, History, FileText, CheckCircle, Clock, Loader2 } from 'lucide-react';
import { getApiError } from '../utils/api';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

const WalletPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [payments, setPayments] = useState([]);
  const [transactions, setTransactions] = useState([]);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [meRes, payRes, txnRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/payments/my-payments`, { credentials: 'include' }),
        fetch(`${API}/student/my-transactions`, { credentials: 'include' }).catch(() => ({ ok: false }))
      ]);
      if (meRes.ok) setUser(await meRes.json());
      if (payRes.ok) setPayments(await payRes.json());
      if (txnRes.ok) setTransactions(await txnRes.json());
    } catch {}
    setLoading(false);
  };

  const downloadReceipt = (paymentId) => {
    const token = localStorage.getItem('token');
    window.open(`${API}/payments/receipt-pdf/${paymentId}?token=${token}`, '_blank');
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button onClick={() => navigate(-1)} variant="outline" className="rounded-full" data-testid="back-button">
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <h1 className="text-xl font-bold text-slate-900">Wallet & Receipts</h1>
          </div>
          <Button onClick={() => navigate('/browse-classes')} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full font-bold" data-testid="recharge-btn">
            <IndianRupee className="w-4 h-4 mr-1" /> Recharge
          </Button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Balance Card */}
        <div className="bg-gradient-to-r from-sky-500 to-sky-600 rounded-3xl p-8 text-white mb-8 shadow-xl shadow-sky-200">
          <p className="text-sky-100 text-sm font-medium mb-1">Available Balance</p>
          <p className="text-4xl font-black flex items-center" data-testid="wallet-balance">
            <IndianRupee className="w-8 h-8" />{(user?.credits || 0).toLocaleString()}
          </p>
          <p className="text-sky-200 text-xs mt-2">Credits</p>
        </div>

        {/* Payment Receipts */}
        <div className="mb-8">
          <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-500" /> Payment Receipts
          </h2>
          {payments.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
              No payments yet
            </div>
          ) : (
            <div className="space-y-3">
              {payments.map(p => (
                <div key={p.payment_id} className="bg-white rounded-2xl border border-slate-200 p-4 flex items-center justify-between hover:shadow-sm transition-shadow" data-testid={`receipt-${p.payment_id}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${p.status === 'paid' ? 'bg-emerald-100' : 'bg-amber-100'}`}>
                      {p.status === 'paid' ? <CheckCircle className="w-5 h-5 text-emerald-600" /> : <Clock className="w-5 h-5 text-amber-600" />}
                    </div>
                    <div>
                      <p className="font-semibold text-slate-900 text-sm">
                        {p.type === 'recharge' ? `Credit Recharge (${p.credits} credits)` : (p.learning_plan_name || 'Class Assignment')}
                      </p>
                      <p className="text-xs text-slate-500">
                        {p.teacher_name && `Teacher: ${p.teacher_name} | `}
                        {p.created_at ? new Date(p.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : ''}
                      </p>
                      <p className="text-[10px] text-slate-400 font-mono">{p.receipt_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="font-bold text-slate-900 flex items-center"><IndianRupee className="w-3.5 h-3.5" />{p.amount?.toLocaleString()}</p>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${p.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{p.status?.toUpperCase()}</span>
                    </div>
                    {p.status === 'paid' && (
                      <Button variant="outline" size="sm" className="rounded-full" onClick={() => downloadReceipt(p.payment_id)} data-testid={`download-receipt-${p.payment_id}`}>
                        <Download className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Credit Transactions */}
        {transactions.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <History className="w-5 h-5 text-violet-500" /> Transaction History
            </h2>
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left p-3 text-xs text-slate-500">Date</th>
                    <th className="text-left p-3 text-xs text-slate-500">Description</th>
                    <th className="text-right p-3 text-xs text-slate-500">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(t => (
                    <tr key={t.transaction_id} className="border-t border-slate-100">
                      <td className="p-3 text-xs text-slate-600">{t.created_at ? new Date(t.created_at).toLocaleDateString() : '-'}</td>
                      <td className="p-3 text-xs font-medium">{t.description}</td>
                      <td className={`p-3 text-right text-xs font-bold ${t.type === 'debit' ? 'text-red-600' : 'text-emerald-600'}`}>
                        {t.type === 'debit' ? '-' : '+'}{t.amount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WalletPage;
