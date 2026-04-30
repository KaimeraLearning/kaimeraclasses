import React, { useState } from 'react';
import { Lock, Eye, EyeOff, Save } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { API, apiFetch, getApiError } from '../utils/api';

/**
 * Forced password change modal — shown after login when the server
 * returns `must_change_password: true` (i.e. the account was created with
 * an admin-/system-generated temporary password). The user cannot dismiss
 * this dialog without setting a real password.
 *
 * Props:
 *   - onSuccess(): called once the new password has been saved successfully.
 *                  Parent should then proceed to redirect by role.
 */
export default function ForcePasswordChangeModal({ onSuccess }) {
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (pwd.length < 6) { toast.error('Password must be at least 6 characters'); return; }
    if (pwd !== confirm) { toast.error('Passwords do not match'); return; }
    setBusy(true);
    try {
      const r = await apiFetch(`${API}/auth/change-password`, {
        method: 'POST', credentials: 'include',
        body: JSON.stringify({ new_password: pwd }),
      });
      if (!r.ok) throw new Error(await getApiError(r));
      toast.success('Password updated — you can now use your dashboard.');
      // Update locally cached user so we don't show this again on rehydrate.
      try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        u.must_change_password = false;
        localStorage.setItem('user', JSON.stringify(u));
      } catch (_) { /* ignore */ }
      onSuccess && onSuccess();
    } catch (err) {
      toast.error(err.message || 'Failed to update password');
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4" data-testid="force-password-modal">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="bg-gradient-to-br from-sky-500 to-violet-600 px-6 py-5 text-white text-center">
          <Lock className="w-10 h-10 mx-auto mb-2" />
          <h2 className="text-xl font-bold">Set Your Password</h2>
          <p className="text-xs text-white/80 mt-1">
            For security, please replace the temporary password we emailed to you with one only you know.
          </p>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <Label className="text-xs">New password</Label>
            <div className="relative">
              <Input
                type={show ? 'text' : 'password'}
                value={pwd}
                onChange={(e) => setPwd(e.target.value)}
                placeholder="At least 6 characters"
                className="rounded-xl pr-10"
                data-testid="force-pwd-new"
                autoFocus
              />
              <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <Label className="text-xs">Confirm new password</Label>
            <Input
              type={show ? 'text' : 'password'}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Type it again"
              className="rounded-xl"
              data-testid="force-pwd-confirm"
            />
          </div>
          <Button type="submit" disabled={busy} className="w-full bg-gradient-to-r from-sky-500 to-violet-600 hover:opacity-90 text-white rounded-full" data-testid="force-pwd-submit">
            <Save className="w-4 h-4 mr-1" />
            {busy ? 'Saving…' : 'Save & Continue'}
          </Button>
          <p className="text-[11px] text-slate-400 text-center">You won't be able to use the temporary password again after this.</p>
        </form>
      </div>
    </div>
  );
}
