import React, { useEffect, useState } from 'react';
import { Wrench, AlertCircle, Loader2, CheckCircle2, XCircle, RefreshCw, Eye } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { toast } from 'sonner';
import { API, apiFetch, getApiError } from '../utils/api';

/**
 * "System Repair" button — runs every idempotent data-reconciliation task on the
 * backend (`/api/admin/system/repair`) and shows a per-task report.
 *
 * Safe to click as often as needed: the backend tasks never delete users,
 * transactions, balances, complaints, or anything else of value — they only
 * fix orphans, normalize signs, and backfill missing fields.
 */
export default function SystemRepairButton() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  // Read-only preview of duplicate class groups the repair would act on.
  const [duplicates, setDuplicates] = useState(null);

  const loadDiagnostic = async () => {
    try {
      const r = await apiFetch(`${API}/admin/system/diagnose`, { credentials: 'include' });
      if (!r.ok) return;
      const data = await r.json();
      setDuplicates(data);
    } catch (_) { /* silent */ }
  };

  useEffect(() => {
    if (open) loadDiagnostic();
  }, [open]);

  const run = async () => {
    setBusy(true);
    setReport(null);
    try {
      const r = await apiFetch(`${API}/admin/system/repair`, {
        method: 'POST', credentials: 'include',
      });
      if (!r.ok) throw new Error(await getApiError(r));
      const data = await r.json();
      setReport(data);
      const totalFixed = data.total_fixed || 0;
      if (totalFixed === 0) {
        toast.success('System is already healthy — nothing to fix.');
      } else {
        toast.success(`Repair complete — ${totalFixed} item(s) fixed.`);
      }
      // Refresh duplicates preview so subsequent re-runs reflect current state.
      loadDiagnostic();
    } catch (e) {
      toast.error(e.message || 'Repair failed');
    } finally { setBusy(false); }
  };

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-full font-semibold"
        data-testid="system-repair-btn"
      >
        <Wrench className="w-4 h-4 mr-2" />
        System Repair
      </Button>

      <Dialog open={open} onOpenChange={(v) => !busy && setOpen(v)}>
        <DialogContent className="max-w-2xl rounded-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wrench className="w-5 h-5 text-amber-500" />
              System Repair
            </DialogTitle>
          </DialogHeader>

          {/* Preview of what's broken (read-only diagnose) */}
          {!report && duplicates && (
            <div className="space-y-3" data-testid="repair-preview">
              <div className={`rounded-xl p-3 ${duplicates.total_groups === 0 ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'}`}>
                <div className="flex items-center gap-2">
                  {duplicates.total_groups === 0 ? (
                    <><CheckCircle2 className="w-5 h-5 text-emerald-600" /><span className="font-semibold text-emerald-800">No duplicate classes found</span></>
                  ) : (
                    <><Eye className="w-5 h-5 text-amber-600" /><span className="font-semibold text-amber-800">{duplicates.total_groups} duplicate group(s) detected — preview below</span></>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Click <strong>Run Repair</strong> to fix. Duplicates are kept if they have proofs/transactions/attendance.</p>
              </div>

              {duplicates.duplicate_groups.length > 0 && (
                <div className="max-h-[40vh] overflow-y-auto space-y-3">
                  {duplicates.duplicate_groups.map((g, i) => (
                    <div key={i} className="border border-slate-200 rounded-xl p-3 bg-slate-50">
                      <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Reason: {g.reason}</p>
                      <p className="text-xs text-slate-400 font-mono break-all mb-2">{g.key}</p>
                      <div className="space-y-1">
                        {g.classes.map((c, j) => (
                          <div key={c.class_id} className="flex items-center gap-2 text-xs">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${j === 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                              {j === 0 ? 'KEEP' : 'REMOVE'}
                            </span>
                            <span className="font-mono text-[10px] text-slate-500">{c.class_id}</span>
                            <span className="text-slate-700 truncate">{c.title}</span>
                            <span className="text-slate-400 text-[10px] ml-auto">{c.created_at?.slice(0, 16).replace('T', ' ')}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <Button variant="outline" onClick={() => setOpen(false)} className="rounded-full" data-testid="repair-cancel">Cancel</Button>
                <Button onClick={run} disabled={busy} className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-full" data-testid="repair-run">
                  <Wrench className="w-4 h-4 mr-1" /> Run Repair Now
                </Button>
              </div>
            </div>
          )}

          {busy && (
            <div className="py-12 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="w-10 h-10 animate-spin text-amber-500 mb-3" />
              <p className="text-sm">Reconciling data with the latest code rules…</p>
              <p className="text-xs text-slate-400 mt-1">No users, transactions, or balances are being deleted.</p>
            </div>
          )}

          {report && (
            <div className="space-y-3" data-testid="repair-report">
              <div className={`rounded-xl p-3 ${report.total_fixed === 0 ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'}`}>
                <div className="flex items-center gap-2">
                  {report.total_fixed === 0 ? (
                    <><CheckCircle2 className="w-5 h-5 text-emerald-600" /><span className="font-semibold text-emerald-800">System healthy</span></>
                  ) : (
                    <><AlertCircle className="w-5 h-5 text-amber-600" /><span className="font-semibold text-amber-800">{report.total_fixed} item(s) repaired</span></>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1">Run at {new Date(report.ran_at).toLocaleString()}</p>
              </div>

              <div className="max-h-[60vh] overflow-y-auto space-y-1.5">
                {report.tasks.map((t, i) => (
                  <div key={i} className={`flex items-start gap-2 p-2 rounded-lg text-xs ${
                    !t.ok ? 'bg-red-50' : t.count > 0 ? 'bg-blue-50' : 'bg-slate-50'
                  }`}>
                    <div className="flex-shrink-0 mt-0.5">
                      {!t.ok
                        ? <XCircle className="w-4 h-4 text-red-600" />
                        : t.count > 0
                          ? <CheckCircle2 className="w-4 h-4 text-blue-600" />
                          : <CheckCircle2 className="w-4 h-4 text-slate-300" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-slate-800">{t.name}</p>
                      <p className="text-[11px] text-slate-500 break-words">{t.message}</p>
                    </div>
                    <span className={`font-mono font-bold flex-shrink-0 ${t.count > 0 ? 'text-blue-600' : 'text-slate-300'}`}>{t.count}</span>
                  </div>
                ))}
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <Button variant="outline" onClick={() => setOpen(false)} className="rounded-full" data-testid="repair-close">Close</Button>
                <Button onClick={run} disabled={busy} className="bg-amber-500 hover:bg-amber-600 text-white rounded-full" data-testid="repair-rerun">
                  <RefreshCw className="w-4 h-4 mr-1" /> Run Again
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
