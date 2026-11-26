// Non-secret, per-tab hints (which identifier is mid-flow, when the resend cooldown ends, lock deadline).
// This is a UX convenience only: it never grants access and never enforces any rule.
const KEY = 'secure-auth:pending';

export function savePending(data) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ...loadPending(), ...data }));
  } catch {
    /* storage unavailable (private mode): flows still work via router state */
  }
}

export function loadPending() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

export function clearPending() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
