import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authApi } from '../api/auth';
import { setSessionHandler } from '../api/client';

const AuthContext = createContext(null);
const END_CODES = ['SESSION_REPLACED', 'SESSION_EXPIRED', 'SESSION_ENDED'];
const EMPTY = { user: null, session: null, biometricEnrolled: null };

/**
 * The server is the only source of truth. This context just mirrors it:
 * - on load it asks GET /me,
 * - any API 401 about the session (replaced on another device, expired, ended) flips it to signed-out
 *   instantly, which is how the "old device" learns it lost access.
 */
export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading'); // loading | authenticated | anonymous
  const [data, setData] = useState(EMPTY);
  const [endReason, setEndReason] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const res = await authApi.me();
      setData((d) => ({ ...d, user: res.user, session: res.session }));
      setStatus('authenticated');
      setEndReason(null);
    } catch (err) {
      setData(EMPTY);
      setStatus('anonymous');
      setEndReason(END_CODES.includes(err.code) ? err.code : null);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(
    () =>
      setSessionHandler((code) => {
        setData(EMPTY);
        setStatus('anonymous');
        setEndReason(END_CODES.includes(code) ? code : null);
      }),
    [],
  );

  const signIn = useCallback((payload) => {
    setData({ user: payload.user, session: payload.session, biometricEnrolled: payload.biometric_enrolled });
    setStatus('authenticated');
    setEndReason(null);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* even if the call fails, drop local state; the server session simply expires */
    }
    setData(EMPTY);
    setStatus('anonymous');
    setEndReason(null);
  }, []);

  const setBiometricEnrolled = useCallback((value) => setData((d) => ({ ...d, biometricEnrolled: value })), []);
  const clearEndReason = useCallback(() => setEndReason(null), []);

  const value = useMemo(
    () => ({ status, ...data, endReason, refresh, signIn, signOut, setBiometricEnrolled, clearEndReason }),
    [status, data, endReason, refresh, signIn, signOut, setBiometricEnrolled, clearEndReason],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
