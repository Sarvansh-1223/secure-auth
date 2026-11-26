import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import Input from '../components/Input';
import { AuthLayout, CardHeading } from '../components/Layout';
import { ShieldIcon } from '../components/Icons';
import { savePending } from '../utils/pending';
import {
  cleanPhone, todayISO, validateDob, validateEmail, validatePhone, validateSurname,
} from '../utils/validators';

export default function Register() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('email');
  const [form, setForm] = useState({ email: '', phone: '', surname: '', dob: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    if (errors[k]) setErrors((x) => ({ ...x, [k]: '' }));
  };

  function validate() {
    const next = {
      surname: validateSurname(form.surname),
      dob: validateDob(form.dob),
      [mode]: mode === 'email' ? validateEmail(form.email) : validatePhone(form.phone),
    };
    setErrors(next);
    return !Object.values(next).some(Boolean);
  }

  async function onSubmit(e) {
    e.preventDefault();
    setFormError('');
    if (!validate()) return;
    setBusy(true);
    try {
      const payload = { surname: form.surname.trim(), date_of_birth: form.dob };
      if (mode === 'email') payload.email = form.email.trim();
      else payload.phone = cleanPhone(form.phone.trim());
      const res = await authApi.register(payload);
      savePending({ identifier: res.identifier, kind: res.channel, purpose: 'register', cooldownUntil: Date.now() + 30000 });
      navigate('/verify', { state: { identifier: res.identifier, channel: res.channel } });
    } catch (err) {
      if (err.code === 'VALIDATION_ERROR') {
        const d = err.details || {};
        setErrors({
          email: d.email?.[0], phone: d.phone?.[0], surname: d.surname?.[0], dob: d.date_of_birth?.[0],
        });
        setFormError(d.identifier?.[0] || '');
      } else if (err.code === 'RATE_LIMITED') {
        setFormError('Too many sign-up attempts. Please try again later.');
      } else {
        setFormError(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout back={{ to: '/', label: 'Home' }}>
      <CardHeading icon={<ShieldIcon size={22} />} title="Create your account" subtitle="We’ll send a code to verify your email or mobile number." />
      <form className="stack" onSubmit={onSubmit} noValidate>
        <div className="segmented" role="radiogroup" aria-label="Register with">
          {[['email', 'Email'], ['phone', 'Mobile number']].map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={mode === value}
              className={`segmented__item ${mode === value ? 'is-active' : ''}`}
              onClick={() => { setMode(value); setErrors({}); setFormError(''); }}
            >
              {label}
            </button>
          ))}
        </div>

        {mode === 'email' ? (
          <Input label="Email address" type="email" autoComplete="email" inputMode="email" placeholder="you@company.com"
            value={form.email} onChange={set('email')} error={errors.email} autoFocus />
        ) : (
          <Input label="Mobile number" type="tel" autoComplete="tel" inputMode="tel" placeholder="+14155552671"
            hint="International format with country code." value={form.phone} onChange={set('phone')} error={errors.phone} autoFocus />
        )}

        <div className="grid-2">
          <Input label="Surname" autoComplete="family-name" value={form.surname} onChange={set('surname')} error={errors.surname} maxLength={100} />
          <Input label="Date of birth" type="date" autoComplete="bday" max={todayISO()} value={form.dob} onChange={set('dob')} error={errors.dob} />
        </div>

        <Alert variant="error">{formError}</Alert>
        <Button type="submit" full loading={busy}>Send verification code</Button>
        <p className="muted center small">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
