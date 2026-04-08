import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, Wallet, ArrowUpRight, ArrowDownLeft, Clock, Loader2, CreditCard, Building, Save } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const WalletPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bankForm, setBankForm] = useState({ account_name: '', account_number: '', bank_name: '', ifsc_code: '' });
  const [savingBank, setSavingBank] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [userRes, walletRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/wallet/summary`, { credentials: 'include' })
      ]);
      if (!userRes.ok) { navigate('/login'); return; }
      const userData = await userRes.json();
      setUser(userData);
      if (walletRes.ok) {
        const w = await walletRes.json();
        setWallet(w);
        if (w.bank_details) setBankForm(w.bank_details);
      }
    } catch { toast.error('Failed to load wallet'); }
    finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSaveBankDetails = async () => {
    if (!bankForm.account_name || !bankForm.account_number || !bankForm.bank_name) {
      toast.error('Please fill all bank fields');
      return;
    }
    setSavingBank(true);
    try {
      const res = await fetch(`${API}/teacher/update-profile`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bank_details: bankForm })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Bank details saved!');
    } catch (err) { toast.error(err.message); }
    finally { setSavingBank(false); }
  };

  const backPath = user?.role === 'teacher' ? '/teacher-dashboard'
    : user?.role === 'student' ? '/student-dashboard'
    : user?.role === 'admin' ? '/admin-dashboard'
    : '/counsellor-dashboard';

  const formatDate = (d) => {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
    catch { return d; }
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
          <Button variant="ghost" onClick={() => navigate(backPath)} className="rounded-full" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>Wallet</h1>
            <p className="text-xs text-slate-500">Balance & transaction history</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Balance Card */}
        <div className="bg-gradient-to-br from-sky-500 via-sky-600 to-violet-600 rounded-3xl p-8 text-white shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
          <div className="flex items-center gap-3 mb-2">
            <Wallet className="w-8 h-8 text-white/80" />
            <span className="text-sky-100 text-sm font-medium">Current Balance</span>
          </div>
          <p className="text-5xl font-bold mb-1" data-testid="wallet-balance">{wallet?.balance?.toFixed(2) || '0.00'}</p>
          <p className="text-sky-200 text-sm">credits</p>
          {wallet?.pending_earnings > 0 && (
            <div className="mt-4 bg-white/10 rounded-xl px-4 py-3">
              <p className="text-sky-100 text-xs font-medium">Pending Earnings</p>
              <p className="text-xl font-bold text-amber-300" data-testid="pending-earnings">+{wallet.pending_earnings.toFixed(2)} credits</p>
              <p className="text-sky-200 text-xs">Awaiting admin approval</p>
            </div>
          )}
        </div>

        {/* Bank Details (Teachers only) */}
        {user?.role === 'teacher' && (
          <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Building className="w-5 h-5 text-sky-500" /> Bank Details
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-sm text-slate-600">Account Holder Name</Label>
                <Input value={bankForm.account_name} onChange={e => setBankForm({...bankForm, account_name: e.target.value})}
                  className="rounded-xl border-2 border-slate-200" placeholder="Full name" data-testid="bank-name-input" />
              </div>
              <div>
                <Label className="text-sm text-slate-600">Account Number</Label>
                <Input value={bankForm.account_number} onChange={e => setBankForm({...bankForm, account_number: e.target.value})}
                  className="rounded-xl border-2 border-slate-200" placeholder="Account number" data-testid="bank-account-input" />
              </div>
              <div>
                <Label className="text-sm text-slate-600">Bank Name</Label>
                <Input value={bankForm.bank_name} onChange={e => setBankForm({...bankForm, bank_name: e.target.value})}
                  className="rounded-xl border-2 border-slate-200" placeholder="Bank name" data-testid="bank-bank-input" />
              </div>
              <div>
                <Label className="text-sm text-slate-600">IFSC Code</Label>
                <Input value={bankForm.ifsc_code} onChange={e => setBankForm({...bankForm, ifsc_code: e.target.value})}
                  className="rounded-xl border-2 border-slate-200" placeholder="IFSC code" data-testid="bank-ifsc-input" />
              </div>
            </div>
            <Button onClick={handleSaveBankDetails} disabled={savingBank}
              className="mt-4 bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6" data-testid="save-bank-btn">
              {savingBank ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              Save Bank Details
            </Button>
          </div>
        )}

        {/* Buy Credits (Students only) */}
        {user?.role === 'student' && (
          <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6 text-center">
            <CreditCard className="w-10 h-10 text-sky-500 mx-auto mb-3" />
            <h3 className="font-bold text-slate-900 mb-2">Need more credits?</h3>
            <Button onClick={() => navigate('/browse-classes')} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-8" data-testid="buy-credits-btn">
              Buy Credits
            </Button>
          </div>
        )}

        {/* Transaction History */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
          <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-sky-500" /> Transaction History
          </h3>
          {(!wallet?.transactions || wallet.transactions.length === 0) ? (
            <p className="text-center text-slate-400 py-8">No transactions yet</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {wallet.transactions.map((txn, i) => {
                const isPositive = txn.amount > 0;
                return (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 transition-colors border border-slate-100" data-testid={`txn-${i}`}>
                    <div className="flex items-center gap-3">
                      {isPositive ? (
                        <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                          <ArrowDownLeft className="w-5 h-5 text-emerald-600" />
                        </div>
                      ) : (
                        <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
                          <ArrowUpRight className="w-5 h-5 text-red-600" />
                        </div>
                      )}
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{txn.description}</p>
                        <p className="text-xs text-slate-400">{formatDate(txn.created_at)}</p>
                      </div>
                    </div>
                    <span className={`font-bold text-sm ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                      {isPositive ? '+' : ''}{txn.amount}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WalletPage;
