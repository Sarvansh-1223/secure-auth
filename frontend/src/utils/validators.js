// Client-side validation is for UX only. The server re-validates everything and is the authority.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const SURNAME_RE = /^\p{L}+(?:[ '’.-]\p{L}+)*\.?$/u;

export const MIN_AGE = 13;
export const MAX_AGE = 120;

export function cleanPhone(value) {
  return value.replace(/[\s().-]/g, '');
}

export function validateEmail(value) {
  const v = value.trim();
  if (!v) return 'Enter your email address.';
  if (!EMAIL_RE.test(v)) return 'Enter a valid email address.';
  return '';
}

export function validatePhone(value) {
  const v = cleanPhone(value.trim());
  if (!v) return 'Enter your mobile number.';
  if (!v.startsWith('+')) return 'Use international format, starting with + and the country code (e.g. +14155552671).';
  if (!/^\+[1-9]\d{6,14}$/.test(v)) return 'Enter a valid international phone number.';
  return '';
}

export function validateSurname(value) {
  const v = value.trim();
  if (!v) return 'Surname is required.';
  if (v.length > 100) return 'Surname must be 100 characters or fewer.';
  if (!SURNAME_RE.test(v)) return 'Use letters, spaces, hyphens and apostrophes only.';
  return '';
}

export function todayISO() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

export function validateDob(value) {
  if (!value) return 'Date of birth is required.';
  const [y, m, d] = value.split('-').map(Number);
  const dob = new Date(y, m - 1, d);
  if (Number.isNaN(dob.getTime()) || dob.getFullYear() !== y || dob.getMonth() !== m - 1 || dob.getDate() !== d) {
    return 'Enter a valid date of birth.';
  }
  const now = new Date();
  if (dob > now) return 'Date of birth cannot be in the future.';
  let age = now.getFullYear() - y;
  if (now.getMonth() < m - 1 || (now.getMonth() === m - 1 && now.getDate() < d)) age -= 1;
  if (age > MAX_AGE) return 'Enter a valid date of birth.';
  if (age < MIN_AGE) return `You must be at least ${MIN_AGE} years old.`;
  return '';
}

export function classifyIdentifier(value) {
  return value.includes('@') ? 'email' : 'phone';
}

export function validateIdentifier(value) {
  const v = value.trim();
  if (!v) return 'Enter your email address or mobile number.';
  return classifyIdentifier(v) === 'email' ? validateEmail(v) : validatePhone(v);
}

export function normalizeIdentifier(value) {
  const v = value.trim();
  return classifyIdentifier(v) === 'email' ? v.toLowerCase() : cleanPhone(v);
}

export function maskIdentifier(value = '') {
  if (value.includes('@')) {
    const [name, domain] = value.split('@');
    return `${name.slice(0, 2)}${'•'.repeat(Math.max(name.length - 2, 1))}@${domain}`;
  }
  return `${value.slice(0, 3)}${'•'.repeat(Math.max(value.length - 6, 2))}${value.slice(-3)}`;
}
