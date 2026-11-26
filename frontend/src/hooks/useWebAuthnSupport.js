import { useEffect, useState } from 'react';
import { isPlatformAuthenticatorAvailable, isWebAuthnSupported } from '../api/webauthn';

/** { checked, supported, platform, secure } - drives the "biometrics unavailable" explanations. */
export function useWebAuthnSupport() {
  const [state, setState] = useState({ checked: false, supported: false, platform: false, secure: true });

  useEffect(() => {
    let alive = true;
    (async () => {
      const supported = isWebAuthnSupported();
      const secure = typeof window !== 'undefined' ? window.isSecureContext : true;
      const platform = supported && secure ? await isPlatformAuthenticatorAvailable() : false;
      if (alive) setState({ checked: true, supported, platform, secure });
    })();
    return () => {
      alive = false;
    };
  }, []);

  return state;
}

export function unavailableReason({ supported, secure, platform }) {
  if (!supported) return 'This browser doesn’t support WebAuthn, so biometric sign-in isn’t available here.';
  if (!secure) return 'Biometric sign-in needs a secure connection (HTTPS or localhost).';
  if (!platform) {
    return 'No built-in biometric (Face ID, Touch ID, Windows Hello) was detected on this device. You can still use a phone or security key you registered.';
  }
  return '';
}
