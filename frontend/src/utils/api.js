/**
 * API base path.
 * - If REACT_APP_BACKEND_URL is set at build time, requests go to that absolute backend domain
 *   (e.g. https://api.kaimeraworkspace.com/api/...).
 * - Otherwise falls back to a relative `/api` path (works when frontend and backend share a host
 *   behind a reverse proxy / ingress).
 */
const _BASE = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '');
export const API = _BASE ? `${_BASE}/api` : '/api';

/**
 * Parse API error response and return a user-friendly error message.
 * Handles: JSON with detail field, plain text, network errors, and non-JSON responses.
 */
export async function getApiError(res) {
  try {
    const clone = res.clone();
    const text = await clone.text();
    try {
      const data = JSON.parse(text);
      return data.detail || data.message || data.error || statusMessage(res.status);
    } catch {
      return text || statusMessage(res.status);
    }
  } catch {
    return statusMessage(res.status);
  }
}

function statusMessage(status) {
  const messages = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication failed. Please log in again.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested resource was not found.',
    409: 'Conflict: this action has already been performed.',
    422: 'Invalid input. Please check the form fields.',
    429: 'Too many requests. Please wait and try again.',
    500: 'Server error. Please try again later.',
    502: 'Server temporarily unavailable. Please try again.',
    503: 'Database connection issue. Please try again later.'
  };
  return messages[status] || `Request failed (${status}). Please try again.`;
}
