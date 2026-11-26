// Thin fetch wrapper: JSON in/out, cookies, CSRF header, uniform errors. (No Axios, by requirement.)
const BASE = (import.meta.env.VITE_API_BASE || '/api/v1').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, code, message, details = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const SESSION_CODES = ['SESSION_REPLACED', 'SESSION_ENDED', 'SESSION_EXPIRED', 'SESSION_INVALID'];

let csrfToken = null;
let sessionHandler = null;

/** AuthContext registers here so ANY 401 about the session updates the UI immediately. */
export function setSessionHandler(fn) {
  sessionHandler = fn;
  return () => {
    if (sessionHandler === fn) sessionHandler = null;
  };
}

async function fetchCsrf(force = false) {
  if (csrfToken && !force) return csrfToken;
  const res = await fetch(`${BASE}/auth/csrf`, { credentials: 'include' });
  const data = await res.json();
  csrfToken = data.csrf_token;
  return csrfToken;
}

async function parse(res) {
  if (res.status === 204) return null;
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export async function request(path, { method = 'GET', body, query, signal } = {}, retried = false) {
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method);
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (unsafe) headers['X-CSRFToken'] = await fetchCsrf();

  const qs = query ? `?${new URLSearchParams(query)}` : '';
  let res;
  try {
    res = await fetch(`${BASE}${path}${qs}`, {
      method,
      headers,
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the server. Check your connection and try again.');
  }

  const data = await parse(res);
  if (res.ok) return data;

  const err = data?.error || {};
  if (res.status === 403 && err.code === 'CSRF_FAILED' && !retried) {
    await fetchCsrf(true);
    return request(path, { method, body, query, signal }, true);
  }
  if (res.status === 401 && SESSION_CODES.includes(err.code) && sessionHandler) sessionHandler(err.code);

  throw new ApiError(res.status, err.code || 'ERROR', err.message || 'Something went wrong.', err.details || {});
}
