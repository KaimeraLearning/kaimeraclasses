import React, { useEffect, useState } from 'react';
import { ShieldAlert, RefreshCw, Loader2, CheckCircle2, AlertTriangle, IndianRupee } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { API, apiFetch, getApiError } from '../utils/api';

/**
 * Demo No-Show Audit panel — admin-only.
 *
 * Lists every demo class flagged (or implicitly elapsed) as teacher_no_show in
 * the last N days, with one-click "Re-credit" if the auto-refund didn't run.
 *
 * The backend re-credit is idempotent (skips if a refund txn already exists),
 * so accidental double clicks are safe.
 */
export default function DemoNoShowAudit() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [creditingId, setCreditingId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await apiFetch(`${API}/admin/demo-no-show-audit?days=${days}`, { credentials: 'include' });
      if (!r.ok) throw new Error(await getApiError(r));
      setData(await r.json());
    } catch (e) {
      toast.error(e.message || 'Failed to load audit');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  const recredit = async (classId) => {
    setCreditingId(classId);
    try {
      const r = await apiFetch(`${API}/admin/demo-no-show-audit/recredit/${classId}`, {
        method: 'POST', credentials: 'include',
      });
      if (!r.ok) throw new Error(await getApiError(r));
      const out = await r.json();
      if (out.refunded > 0) {
        toast.success(`Re-credited ${out.refunded} credits.`);
      } else {
        toast.info(out.message || 'Already credited');
      }
      await load();
    } catch (e) {
      toast.error(e.message || 'Re-credit failed');
    } finally { setCreditingId(null); }
  };

  const rows = data?.rows || [];
  const pendingCount = data?.refund_pending_count || 0;

  return (
    <div className="space-y-4" data-testid="demo-no-show-audit">
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-600" />
          <h3 className="text-lg font-bold text-slate-900">Demo No-Show Audit</h3>
          {pendingCount > 0 ? (
            <Badge className="bg-rose-500 text-white" data-testid="pending-refund-badge">
              {pendingCount} refund pending
            </Badge>
          ) : (
            <Badge className="bg-emerald-500 text-white">All clean</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
            data-testid="audit-window-select"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last 1 year</option>
          </select>
          <Button onClick={load} variant="outline" size="sm" disabled={loading} data-testid="audit-refresh-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Demos auto-flagged as teacher no-show. Implicit rows (italic) are past their grace window
        but not yet marked in DB — re-credit will mark + refund atomically.
      </p>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="text-left px-3 py-2">Date</th>
              <th className="text-left px-3 py-2">Class</th>
              <th className="text-left px-3 py-2">Teacher</th>
              <th className="text-left px-3 py-2">Student</th>
              <th className="text-right px-3 py-2">Charged</th>
              <th className="text-right px-3 py-2">Refunded</th>
              <th className="text-center px-3 py-2">Status</th>
              <th className="text-center px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-slate-500">
                  {loading ? 'Loading…' : `No no-show demos in the last ${days} days.`}
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr
                  key={r.class_id}
                  className={`border-t border-slate-100 ${r.implicit ? 'italic bg-amber-50/40' : ''}`}
                  data-testid={`audit-row-${r.class_id}`}
                >
                  <td className="px-3 py-2 whitespace-nowrap">{r.date}<span className="text-xs text-slate-500"> {r.end_time}</span></td>
                  <td className="px-3 py-2 max-w-[220px] truncate" title={r.title}>{r.title}</td>
                  <td className="px-3 py-2">{r.teacher_name || '—'}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium">{r.student_name || '—'}</div>
                    <div className="text-xs text-slate-500">{r.student_email}</div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums"><IndianRupee className="w-3 h-3 inline" />{r.amount_charged}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-emerald-700"><IndianRupee className="w-3 h-3 inline" />{r.amount_refunded}</td>
                  <td className="px-3 py-2 text-center">
                    {r.refund_pending ? (
                      <Badge className="bg-rose-500 text-white"><AlertTriangle className="w-3 h-3 mr-1" /> Pending</Badge>
                    ) : r.amount_charged === 0 ? (
                      <Badge variant="outline" className="text-slate-500">Free demo</Badge>
                    ) : (
                      <Badge className="bg-emerald-500 text-white"><CheckCircle2 className="w-3 h-3 mr-1" /> Refunded</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {r.refund_pending && r.amount_charged > 0 ? (
                      <Button
                        size="sm"
                        onClick={() => recredit(r.class_id)}
                        disabled={creditingId === r.class_id}
                        className="bg-rose-500 hover:bg-rose-600 text-white text-xs"
                        data-testid={`recredit-${r.class_id}`}
                      >
                        {creditingId === r.class_id ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Re-credit'}
                      </Button>
                    ) : (
                      <span className="text-slate-400 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
