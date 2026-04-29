/**
 * Determine if a transaction is an outflow (debit) or inflow (credit)
 * for the user it belongs to. Used to color and sign-prefix amount cells in
 * wallet/ledger UIs.
 *
 * Robust to BOTH:
 *  - new transactions stored with proper signs (-ve = outflow, +ve = inflow)
 *  - legacy transactions stored as +ve regardless of direction (we infer from type)
 */
const OUTFLOW_TYPES = new Set([
  'demo_booking',
  'class_booking',
  'class_purchase',
  'credit_deduct',
  'debit',
  'payout_to_teacher',
  'admin_payout',
  'refund_issued',
]);

const INFLOW_TYPES = new Set([
  'recharge',
  'credit_add',
  'class_delete_refund',
  'class_deleted_by_admin',
  'earning',
  'payout',
  'demo_payout',
  'class_payout',
  'admin_topup',
  'admin_credit_received',
]);

export function txDirection(t) {
  if (!t) return 'inflow';
  if (typeof t.amount === 'number' && t.amount < 0) return 'outflow';
  if (OUTFLOW_TYPES.has(t.type)) return 'outflow';
  if (INFLOW_TYPES.has(t.type)) return 'inflow';
  // Default: positive amount = inflow
  return 'inflow';
}

export function txDisplayAmount(t) {
  const dir = txDirection(t);
  const abs = Math.abs(Number(t.amount) || 0);
  return dir === 'outflow' ? `-${abs}` : `+${abs}`;
}

export function txAmountClass(t) {
  return txDirection(t) === 'outflow' ? 'text-red-600' : 'text-emerald-600';
}
