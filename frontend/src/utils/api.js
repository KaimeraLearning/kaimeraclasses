/** API base path — always relative so it works on any deployed domain */
export const API = "/api";

/**
 * Parse API error response and return a user-friendly error message.
 * Handles: JSON with detail field, plain text, network errors, and non-JSON responses.
 */
export async function getApiError(res) {
  try {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json();
      return data.detail || data.message || data.error || `Request failed (${res.status})`;
    }
    const text = await res.text();
    return text || `Request failed (${res.status})`;
  } catch {
    return `Server error (${res.status}). Please try again.`;
  }
}
