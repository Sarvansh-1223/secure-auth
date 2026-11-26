# Secure Auth: passwordless authentication with device management

React (JavaScript) + Django REST Framework + MySQL. Sign-in is by **six-digit one-time code** (email / SMS) or **real WebAuthn
biometrics** (Face ID, Touch ID, Windows Hello, phones, security keys). One active device per user and the five-failure /
one-hour lockout are enforced **on the server, in the database**.

## Features

| Requirement | How it is implemented |
|---|---|
| Registration (email *or* phone, DOB, surname) | `accounts/`: strict validation, E.164 phones, unique email / phone, enumeration-safe `202` response, verification code before the account can sign in |
| OTP login | `otp/`: CSPRNG 6-digit codes, stored only as salted HMAC, 5-min TTL (configurable), single use, per-code attempt cap, resend cooldown + hourly cap |
| Face ID / biometrics | `webauthn_app/` with `py_webauthn`: server-stored single-use challenges, origin / RP-ID / signature / user-verification checks, sign-counter tracking |
| Other biometrics | Same WebAuthn flow with `cross-platform` authenticators (phones, security keys). The app never touches biometric data |
| Single active device | `sessions_app/`: opaque server-side sessions; new login revokes the old one in one transaction; DB constraint `UNIQUE(user, active_slot)`; every request resolves the session in the DB, so the old device loses access immediately |
| Lockout | `security/`: 5 consecutive failures (OTP *and* WebAuthn share one counter) → `locked_until = now + 1h` in the DB; guard runs before any verification; success resets the counter |
| Screens | Landing, Register, Verify, Login, OTP, Biometric, Session Replaced, Account Locked, Dashboard, Security Settings |

## Project layout

```
backend/   Django project (config, core, accounts, otp, sessions_app, webauthn_app, security, tests)
frontend/  Vite + React (api/, components/, context/, hooks/, pages/, styles/, utils/)
docs/      API.md, ARCHITECTURE.md
```

## Screenshots

Captured from a real browser run (`docs/screenshots/`): landing, register, verify, dashboard, security settings, login,
biometric, mobile OTP, mobile dashboard, session replaced, wrong code, account locked.

## Run it locally

Prerequisites: Python 3.11+, Node 18+, MySQL 8+ (and `libmysqlclient-dev` / `mysql-client` headers for `mysqlclient`).

### 1. Database

```sql
CREATE DATABASE secure_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'secure_auth'@'localhost' IDENTIFIED BY 'Auth@1205';
GRANT ALL PRIVILEGES ON secure_auth.* TO 'secure_auth'@'localhost';
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/make_env.py        # writes .env with fresh random SECRET_KEY / AUTH_PEPPER
# edit .env: set DB_PASSWORD to the password from step 1
python manage.py migrate
python manage.py runserver        # http://127.0.0.1:8000
```

With `DEBUG=True` (the default `.env.example`) email codes print in the **server terminal** (console email backend) and SMS
codes are logged by the console provider. This is the only way codes are exposed, and it is refused when `DEBUG=False`. For real delivery
set `EMAIL_BACKEND=…smtp…` plus `EMAIL_HOST*`, and `SMS_PROVIDER=twilio` with the `TWILIO_*` variables.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

Always open **`http://localhost:5173`** (not 127.0.0.1): the WebAuthn RP ID is `localhost`. Vite proxies `/api` to Django, so
the browser sees one origin and cookies are first-party.

### Tests

```bash
cd backend && DB_ENGINE=sqlite python manage.py test tests   # 40 tests, no MySQL needed
```

The suite includes a software WebAuthn authenticator, so registration and sign-in are verified end to end (signature,
challenge replay, wrong origin, tampered signature) without a browser. It also covers lockout timing, simultaneous
devices, session revocation, OTP expiry / reuse, CSRF and enumeration parity.

### Trying the biometrics

1. Register, verify the code (printed in the Django terminal) → you land on the dashboard.
2. Click **Set up biometrics** (Touch ID / Windows Hello / Face ID prompt appears).
3. Sign out, choose **Use Face ID / Touch ID / Windows Hello** on the login screen.
4. For the two-device demo, sign in from a second browser profile: the first one shows **Signed in on another device** on its next request.

## Configuration

All values are environment variables (see `backend/.env.example`). Notable ones: `OTP_TTL_SECONDS` (300),
`OTP_RESEND_COOLDOWN_SECONDS` (30), `OTP_MAX_SENDS_PER_HOUR` (5), `LOCKOUT_MAX_FAILURES` (5), `LOCKOUT_DURATION_SECONDS` (3600),
`SESSION_IDLE_TIMEOUT_SECONDS` (1800), `SESSION_ABSOLUTE_TIMEOUT_SECONDS` (43200), `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGINS`.

## Assumptions

1. **No passwords** exist, so there is nothing to hash. Users have unusable passwords; identity is proven by OTP or WebAuthn.
2. Verifying the registration code also signs the user in (the code proves ownership) and applies the single-device policy.
3. Biometrics can only be enrolled by a signed-in user; SMS needs a provider account, so dev mode logs it server-side.
4. DOB must imply an age of 13–120 (configurable). Sessions idle out after 30 min and last 12 h at most.
5. Requesting a code is not a "failure". Failures are wrong codes and failed biometric assertions, counted together per account.

## Security decisions

- **Opaque server-side sessions, no JWT**: revocation must be instant. Only the SHA-256 of the token is stored. Cookie is
  `HttpOnly; SameSite=Lax; Secure` (Secure off only in DEBUG).
- **OTP**: `secrets`-based, salted HMAC-SHA256 with a server pepper, constant-time compare, atomic consume (replay / race safe), per-code attempt cap.
- **Anti-enumeration**: identical responses and status codes for registered / unknown identifiers on register, request-code, verify, WebAuthn options and
  lockout status. Unknown identifiers get a lockout row too, so "locked" proves nothing.
- **Single device**: row lock on the user + revoke-then-insert in one transaction, backed by `UNIQUE(user, active_slot)` (MySQL has no partial indexes, so a NULL-able slot column is used).
- **CSRF** enforced on every unsafe request, including unauthenticated ones. CORS is restricted to configured origins with credentials.
- **Per-IP failure limiter** and DRF throttles add brute-force resistance; throttles use the Django cache (use Redis in production).
- Secrets only come from the environment; `.env` is git-ignored.

## Known limitations (honest scope)

- **Lockout is a DoS vector by design**: anyone who knows an identifier can lock that account for an hour. This follows directly from the required rule; per-IP limiting and audit logging reduce but do not remove it.
- Real SMS and email delivery need provider credentials. Only the console providers were exercised.
- The default cache is in-process (`LocMemCache`): resend cooldowns and DRF throttles are per-process. Set `REDIS_URL` for multi-worker deployments. Lockout, OTP and session state live in the database and are unaffected.
- HTTPS is required in production (`DEBUG=False` turns on secure cookies, HSTS and SSL redirect). A reverse proxy and `TRUST_PROXY` setup are not included.
- **Tested on SQLite, not MySQL.** The suite runs on SQLite. The MySQL settings and migrations were not executed in this environment (the `mysqlclient` build failed here), so run `migrate` against MySQL on your machine and re-run the tests there before relying on it.
- Browser biometrics were exercised end to end with Chromium's **virtual authenticator**, not real Face ID / Touch ID hardware. The server side is verified with the software authenticator; test the actual prompt on your device.
