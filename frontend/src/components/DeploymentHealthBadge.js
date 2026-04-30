import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { API, apiFetch } from '../utils/api';

/**
 * Deployment Health Badge — admin header chip that polls /api/health/config
 * and surfaces production-sync issues at a glance.
 *
 * Resolves the recurring problem where users test on a deployed domain that
 * hasn't pulled the latest backend env (e.g. missing API_KEY, SMTP creds).
 *
 * Click for full breakdown.
 */
export default function DeploymentHealthBadge() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await apiFetch(`${API}/health/config`);
      if (!r.ok) { setData({ error: `HTTP ${r.status}` }); return; }
      setData(await r.json());
    } catch (e) {
      setData({ error: e.message || 'fetch failed' });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const status = (() => {
    if (!data) return 'loading';
    if (data.error) return 'error';
    const required = ['MONGO_URL', 'DB_NAME', 'SENDER_EMAIL', 'GMAIL_APP_PASSWORD'];
    const missing = required.filter((k) => !data.env?.[k]?.set);
    if (missing.length > 0) return 'warn';
    if (!data.smtp_587_reachable) return 'warn';
    if (!data.system_pricing_seeded) return 'warn';
    return 'ok';
  })();

  const variant = {
    loading: { cls: 'bg-slate-200 text-slate-600', icon: Loader2, label: 'Health' },
    ok:      { cls: 'bg-emerald-500 text-white',   icon: CheckCircle2, label: 'Healthy' },
    warn:    { cls: 'bg-amber-500 text-white',     icon: AlertTriangle, label: 'Check' },
    error:   { cls: 'bg-rose-500 text-white',      icon: AlertTriangle, label: 'Error' },
  }[status];
  const Icon = variant.icon;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${variant.cls}`}
        data-testid="deployment-health-badge"
        title="Deployment health (env / SMTP / pricing)"
      >
        <Icon className={`w-3 h-3 ${status === 'loading' ? 'animate-spin' : ''}`} />
        {variant.label}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl" data-testid="deployment-health-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-sky-600" /> Deployment Health
            </DialogTitle>
          </DialogHeader>

          {!data ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : data.error ? (
            <div className="text-sm text-rose-700">Failed to fetch health: {data.error}</div>
          ) : (
            <div className="space-y-3 text-sm">
              <p className="text-xs text-slate-500">
                Use this when something works in preview but fails on the deployed domain — usually
                it's a missing env var. Push to GitHub and redeploy if anything is red.
              </p>

              <div>
                <h5 className="font-semibold text-slate-900 mb-2">Environment</h5>
                <ul className="space-y-1">
                  {Object.entries(data.env || {}).map(([k, v]) => (
                    <li key={k} className="flex items-center justify-between bg-slate-50 px-3 py-1.5 rounded-lg">
                      <code className="text-xs">{k}</code>
                      {v.set ? (
                        <Badge className="bg-emerald-500 text-white text-[10px]">set ({v.length} chars)</Badge>
                      ) : (
                        <Badge className="bg-rose-500 text-white text-[10px]">missing</Badge>
                      )}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 rounded-lg p-2 flex items-center justify-between">
                  <span>SMTP 587 reachable</span>
                  {data.smtp_587_reachable
                    ? <Badge className="bg-emerald-500 text-white">yes</Badge>
                    : <Badge className="bg-rose-500 text-white">no</Badge>}
                </div>
                <div className="bg-slate-50 rounded-lg p-2 flex items-center justify-between">
                  <span>Pricing seeded</span>
                  {data.system_pricing_seeded
                    ? <Badge className="bg-emerald-500 text-white">yes</Badge>
                    : <Badge className="bg-rose-500 text-white">no</Badge>}
                </div>
                <div className="bg-slate-50 rounded-lg p-2 flex items-center justify-between col-span-2">
                  <span>DB name (runtime)</span>
                  <code className="text-[11px]">{data.db_name_runtime}</code>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={load} variant="outline" size="sm" disabled={loading} data-testid="refresh-health">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Refresh'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
