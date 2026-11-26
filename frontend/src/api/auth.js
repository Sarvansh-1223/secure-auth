import { request } from './client';

export const authApi = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  registerResend: (identifier) => request('/auth/register/resend', { method: 'POST', body: { identifier } }),
  registerVerify: (identifier, code) => request('/auth/register/verify', { method: 'POST', body: { identifier, code } }),

  otpRequest: (identifier) => request('/auth/otp/request', { method: 'POST', body: { identifier } }),
  otpResend: (identifier) => request('/auth/otp/resend', { method: 'POST', body: { identifier } }),
  otpVerify: (identifier, code) => request('/auth/otp/verify', { method: 'POST', body: { identifier, code } }),

  webauthnRegisterOptions: (attachment) =>
    request('/webauthn/register/options', { method: 'POST', body: { attachment } }),
  webauthnRegisterVerify: (payload) => request('/webauthn/register/verify', { method: 'POST', body: payload }),
  webauthnAuthOptions: (identifier) =>
    request('/webauthn/authenticate/options', { method: 'POST', body: { identifier } }),
  webauthnAuthVerify: (credential) =>
    request('/webauthn/authenticate/verify', { method: 'POST', body: { credential } }),

  lockoutStatus: (identifier) => request('/auth/lockout-status', { query: { identifier } }),
  me: () => request('/me'),
  logout: () => request('/auth/logout', { method: 'POST', body: {} }),
  securitySettings: () => request('/security/settings'),
  removeCredential: (id) => request(`/security/credentials/${id}`, { method: 'DELETE' }),
};
