import React, { useEffect, useState } from 'react';
import { Database, Loader2, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { API, apiFetch, getApiError } from '../utils/api';

/**
 * Legacy User Migration card — admin-only one-click backfill.
 *
 * Sets `is_verified=true` and `must_change_password=true` for legacy
 * teacher / counsellor / student accounts that pre-date these fields.
 * Idempotent — only fills missing fields, never overwrites.
 */
export default function LegacyUserMigration() {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await apiFetch(`${API}/admin/legacy-user-migration/preview`, { credentials: 'include' });
      if (!r.ok) throw new Error(await getApiError(r));
      setPreview(await r.json());
    } catch (e) {
      toast.error(e.message || 'Failed to load preview');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const run = async () => {
    if (!window.confirm(
      'Run migration?\n\nThis will mark legacy users as verified and force a password change on next login. ' +
      'It is idempotent — only fills missing fields, never overwrites existing data.'
    )) return;
    setRunning(true);
    try {
      const r = await apiFetch(`${API}/admin/legacy-user-migration`, {
        method: 'POST', credentials: 'include',
      });
      if (!r.ok) throw new Error(await getApiError(r));
      const data = await r.json();
      const total = (data.is_verified_set || 0) + (data.must_change_password_set || 0);
      if (total === 0) {
        toast.success('No legacy users needed migration.');
      } else {
        toast.success(`Migrated ${total} field(s) across legacy users.`);
      }
      await load();
    } catch (e) {
      toast.error(e.message || 'Migration failed');
    } finally { setRunning(false); }
  };

  const total = (preview?.missing_is_verified || 0) + (preview?.missing_must_change_password || 0);
  const isClean = preview && total === 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3" data-testid="legacy-user-migration">
      <div className="flex items-center gap-2">
        <Database className="w-5 h-5 text-violet-600" />
        <h4 className="font-bold text-slate-900">Legacy User Migration</h4>
        {isClean ? (
          <Badge className="bg-emerald-500 text-white"><CheckCircle2 className="w-3 h-3 mr-1" /> Clean</Badge>
        ) : preview ? (
          <Badge className="bg-amber-500 text-white">{total} field(s) pending</Badge>
        ) : null}
      </div>

      <p className="text-xs text-slate-600">
        Backfills <code className="bg-slate-100 px-1 rounded">is_verified</code> and
        <code className="bg-slate-100 px-1 rounded mx-1">must_change_password</code> on legacy
        teacher / counsellor / student accounts. Idempotent — safe to re-run anytime.
      </p>

      {preview && (
        <ul className="text-sm text-slate-700 space-y-1">
          <li>• Users missing <code className="text-xs">is_verified</code>: <strong data-testid="missing-verified">{preview.missing_is_verified}</strong></li>
          <li>• Users missing <code className="text-xs">must_change_password</code>: <strong data-testid="missing-must-change">{preview.missing_must_change_password}</strong></li>
        </ul>
      )}

      <Button
        onClick={run}
        disabled={running || loading || isClean}
        className="bg-violet-500 hover:bg-violet-600 text-white"
        data-testid="run-legacy-migration"
      >
        {running ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Database className="w-4 h-4 mr-2" />}
        {isClean ? 'Nothing to migrate' : 'Run Migration'}
      </Button>
    </div>
  );
}
