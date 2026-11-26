// Browser side of WebAuthn. All verification happens on the server; this file only talks to the
// platform (Face ID / Touch ID / Windows Hello / security keys) through navigator.credentials.
import { b64urlToBuffer, bufferToB64url } from '../utils/base64url';

export class WebAuthnClientError extends Error {
  constructor(kind, message) {
    super(message);
    this.kind = kind; // 'unsupported' | 'cancelled' | 'insecure' | 'failed'
  }
}

export function isWebAuthnSupported() {
  return typeof window !== 'undefined' && !!window.PublicKeyCredential && !!navigator.credentials;
}

export async function isPlatformAuthenticatorAvailable() {
  if (!isWebAuthnSupported()) return false;
  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
}

function assertUsable() {
  if (!isWebAuthnSupported()) {
    throw new WebAuthnClientError('unsupported', 'This browser does not support biometric sign-in.');
  }
  if (!window.isSecureContext) {
    throw new WebAuthnClientError('insecure', 'Biometric sign-in requires a secure (HTTPS or localhost) connection.');
  }
}

function mapError(err) {
  if (err instanceof WebAuthnClientError) return err;
  if (err?.name === 'NotAllowedError' || err?.name === 'AbortError') {
    return new WebAuthnClientError('cancelled', 'The request was cancelled or timed out.');
  }
  if (err?.name === 'InvalidStateError') {
    return new WebAuthnClientError('failed', 'This authenticator is already registered for your account.');
  }
  if (err?.name === 'NotSupportedError') {
    return new WebAuthnClientError('unsupported', 'This device does not support the requested authenticator.');
  }
  if (err?.name === 'SecurityError') {
    return new WebAuthnClientError('insecure', 'This site is not allowed to use biometric sign-in here.');
  }
  return new WebAuthnClientError('failed', 'Biometric verification failed.');
}

function serialize(credential) {
  const r = credential.response;
  const out = {
    id: credential.id,
    rawId: bufferToB64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment || undefined,
    clientExtensionResults: credential.getClientExtensionResults?.() || {},
    response: { clientDataJSON: bufferToB64url(r.clientDataJSON) },
  };
  if (r.attestationObject) {
    out.response.attestationObject = bufferToB64url(r.attestationObject);
    out.response.transports = r.getTransports?.() || [];
  }
  if (r.authenticatorData) {
    out.response.authenticatorData = bufferToB64url(r.authenticatorData);
    out.response.signature = bufferToB64url(r.signature);
    if (r.userHandle) out.response.userHandle = bufferToB64url(r.userHandle);
  }
  return out;
}

export async function createCredential(options) {
  assertUsable();
  try {
    const publicKey = {
      ...options,
      challenge: b64urlToBuffer(options.challenge),
      user: { ...options.user, id: b64urlToBuffer(options.user.id) },
      excludeCredentials: (options.excludeCredentials || []).map((c) => ({ ...c, id: b64urlToBuffer(c.id) })),
    };
    const credential = await navigator.credentials.create({ publicKey });
    if (!credential) throw new WebAuthnClientError('cancelled', 'No credential was created.');
    return serialize(credential);
  } catch (err) {
    throw mapError(err);
  }
}

export async function getAssertion(options) {
  assertUsable();
  try {
    const publicKey = {
      ...options,
      challenge: b64urlToBuffer(options.challenge),
      allowCredentials: (options.allowCredentials || []).map((c) => ({ ...c, id: b64urlToBuffer(c.id) })),
    };
    const credential = await navigator.credentials.get({ publicKey });
    if (!credential) throw new WebAuthnClientError('cancelled', 'No credential was returned.');
    return serialize(credential);
  } catch (err) {
    throw mapError(err);
  }
}
