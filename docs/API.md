# API reference

Base path: `/api/v1`. JSON in, JSON out. Authenticated endpoints use the opaque `sa_session` HttpOnly cookie.
Every unsafe method (POST/DELETE), authenticated or not, needs the `X-CSRFToken` header (get it from `GET /auth/csrf`).

## Error envelope

```json
{"error": {"code": "INVALID_CREDENTIALS", "message": "…", "details": {}}}
```

| HTTP | code | meaning |
|---|---|---|
| 400 | `VALIDATION_ERROR` | `details` = `{field: [messages]}` |
| 400 | `INVALID_CREDENTIALS` | wrong / expired / reused code, unknown account (identical for all). `details.remaining_attempts` |
| 400 | `WEBAUTHN_FAILED` | challenge missing / expired / malformed |
| 401 | `NOT_AUTHENTICATED`, `SESSION_INVALID`, `SESSION_ENDED`, `SESSION_EXPIRED` | no / dead session |
| 401 | `SESSION_REPLACED` | the account signed in on another device |
| 403 | `CSRF_FAILED` | missing / bad CSRF token |
| 423 | `ACCOUNT_LOCKED` | `details.retry_after_seconds`, `details.locked_until`; `Retry-After` header |
| 429 | `RESEND_THROTTLED` | resend cooldown / hourly cap. `details.retry_after_seconds` |
| 429 | `RATE_LIMITED` | DRF throttle or per-IP failure limit |

## Endpoints

| Method | URL | Auth | Request | Success response |
|---|---|---|---|---|
| GET | `/auth/csrf` | none | – | `200 {csrf_token}` (also sets cookie) |
| POST | `/auth/register` | none | `{email` **or** `phone, surname, date_of_birth (YYYY-MM-DD)}` | `202 {message, identifier, channel}` (identical for new / pending / already-registered) |
| POST | `/auth/register/resend` | none | `{identifier}` | `202 {message}` |
| POST | `/auth/register/verify` | none | `{identifier, code}` | `200 {user, session, biometric_enrolled}` + cookies |
| POST | `/auth/otp/request` | none | `{identifier}` | `202 {message, expires_in_seconds, resend_after_seconds}` (identical for unknown identifiers) |
| POST | `/auth/otp/resend` | none | `{identifier}` | same as request |
| POST | `/auth/otp/verify` | none | `{identifier, code}` | `200 {user, session, biometric_enrolled}` + cookies |
| POST | `/webauthn/register/options` | session | `{attachment: "platform" \| "cross-platform"}` | `200 {options}` (PublicKeyCredentialCreationOptions JSON) |
| POST | `/webauthn/register/verify` | session | `{credential, nickname?, attachment}` | `201 {credential}` |
| POST | `/webauthn/authenticate/options` | none | `{identifier}` | `200 {options}` (decoy credential for unknown identifiers) |
| POST | `/webauthn/authenticate/verify` | none | `{credential}` | `200 {user, session, biometric_enrolled}` + cookies |
| GET | `/auth/lockout-status?identifier=` | none | – | `200 {locked, retry_after_seconds, locked_until}` |
| GET | `/me` | session | – | `200 {user, session}` |
| GET | `/security/settings` | session | – | `200 {policy, current_session, devices[], credentials[], recent_activity[]}` |
| DELETE | `/security/credentials/{id}` | session | – | `204` |
| POST | `/auth/logout` | session | `{}` | `200 {message}`, session revoked |
| GET | `/health` | none | – | `200 {status}` |

**Device registration and active-session management** happen inside the successful-login services (the device row is upserted
and the previous session revoked in one transaction), so there is no public endpoint that registers a device without authenticating.

## Validation rules

- `email`: valid format, lower-cased. `phone`: must start with `+`, validated by `phonenumbers`, stored as E.164.
- Exactly one of email / phone is required. `surname`: required, letters / spaces / hyphens / apostrophes, ≤ 100.
- `date_of_birth`: valid date, not in the future, age between 13 and 120 (configurable).
- OTP `code`: exactly 6 digits.
