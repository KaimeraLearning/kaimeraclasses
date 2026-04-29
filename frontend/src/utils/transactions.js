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
  // Student-side deductions
  'demo_booking',
  'class_booking',
  'class_purchase',
  'booking',                  // custom-price class booking (legacy positive-stored deduction)
  'assignment_payment',
  // Admin-side / generic
  'credit_deduct',
  'debit',
  'payout_to_teacher',
  'admin_payout',
  'refund_issued',
]);

const INFLOW_TYPES = new Set([
  // Student-side
  'recharge',
  'credit_add',
  'class_delete_refund',
  'class_deleted_by_admin',
  'refund',
  // Teacher-side
  'earning',
  'payout',
  'demo_payout',
  'class_payout',
  // Admin-side
  'admin_topup',
  'admin_credit_received',
  'platform_mirror',          // shows on admin's mirror; sign of `amount` decides display
  'manual_adjustment',        // admin mirror entry for manual credit add/deduct
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
