import { useCallback, useState } from 'react';
import { authApi } from '../api/auth';
import { createCredential, WebAuthnClientError } from '../api/webauthn';

/** Enrol a WebAuthn credential for the signed-in user (options -> authenticator -> server verification). */
export function useBiometricEnrollment(onEnrolled) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const enroll = useCallback(
    async (attachment = 'platform', nickname = '') => {
      setBusy(true);
      setError('');
      try {
        const { options } = await authApi.webauthnRegisterOptions(attachment);
        const credential = await createCredential(options);
        const result = await authApi.webauthnRegisterVerify({ credential, nickname, attachment });
        onEnrolled?.(result.credential);
        return true;
      } catch (err) {
        if (err instanceof WebAuthnClientError && err.kind === 'cancelled') {
          setError('Setup was cancelled. You can try again whenever you’re ready.');
        } else {
          setError(err.message || 'Could not set up biometric sign-in.');
        }
        return false;
      } finally {
        setBusy(false);
      }
    },
    [onEnrolled],
  );

  return { enroll, busy, error, clearError: () => setError('') };
}
