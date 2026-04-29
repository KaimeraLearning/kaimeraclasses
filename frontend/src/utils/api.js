/**
 * API base path.
 * - If REACT_APP_BACKEND_URL is set at build time, requests go to that absolute backend domain
 *   (e.g. https://api.kaimeraworkspace.com/api/...).
 * - Otherwise falls back to a relative `/api` path (works when frontend and backend share a host
 *   behind a reverse proxy / ingress).
 */
const _BASE = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '');
export const API = _BASE ? `${_BASE}/api` : '/api';

const _API_KEY = process.env.REACT_APP_API_KEY || '';

/**
 * Central fetch wrapper that automatically:
 *  - injects the `x-api-key` header on every request
 *  - sets `Content-Type: application/json` when a body is provided and no Content-Type was set
 *  - preserves `credentials: 'include'` for cookie/session auth (overridable)
 *  - leaves all other fetch options (method, body, signal, etc.) untouched
 *
 * Drop-in replacement for `fetch`. Use `apiFetch(url, options)` everywhere instead of `fetch`.
 */
export function apiFetch(url, options = {}) {
  const merged = { ...options };

  // Default to credentials: 'include' (so existing cookie-based auth keeps working),
  // but allow callers to override explicitly.
  if (merged.credentials === undefined) {
    merged.credentials = 'include';
  }

  const headers = new Headers(options.headers || {});
  if (_API_KEY && !headers.has('x-api-key')) {
    headers.set('x-api-key', _API_KEY);
  }
  // Auto-attach Content-Type for JSON bodies when caller didn't set one.
  // Skip for FormData / Blob / URLSearchParams so the browser can set the boundary.
  if (
    merged.body !== undefined &&
    merged.body !== null &&
    !headers.has('Content-Type') &&
    !(typeof FormData !== 'undefined' && merged.body instanceof FormData) &&
    !(typeof Blob !== 'undefined' && merged.body instanceof Blob) &&
    !(typeof URLSearchParams !== 'undefined' && merged.body instanceof URLSearchParams)
  ) {
    headers.set('Content-Type', 'application/json');
  }
  merged.headers = headers;

  return fetch(url, merged);
}

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
