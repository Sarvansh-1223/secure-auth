import { useEffect, useId, useRef } from 'react';

const LENGTH = 6;

/** Six single-digit boxes with paste, arrow/backspace navigation and one-time-code autofill. */
export default function OtpInput({ value, onChange, onComplete, disabled, error, autoFocus = true }) {
  const refs = useRef([]);
  const groupId = useId();
  const digits = Array.from({ length: LENGTH }, (_, i) => value[i] || '');

  useEffect(() => {
    if (autoFocus) refs.current[0]?.focus();
  }, [autoFocus]);

  function commit(next) {
    const clean = next.replace(/\D/g, '').slice(0, LENGTH);
    onChange(clean);
    if (clean.length === LENGTH) onComplete?.(clean);
  }

  function handleChange(i, e) {
    const raw = e.target.value.replace(/\D/g, '');
    if (!raw) return;
    const next = (value.slice(0, i) + raw + value.slice(i + 1)).slice(0, LENGTH);
    commit(next);
    refs.current[Math.min(i + raw.length, LENGTH - 1)]?.focus();
  }

  function handleKeyDown(i, e) {
    if (e.key === 'Backspace') {
      e.preventDefault();
      if (digits[i]) commit(value.slice(0, i) + value.slice(i + 1));
      else if (i > 0) {
        commit(value.slice(0, i - 1) + value.slice(i));
        refs.current[i - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && i > 0) refs.current[i - 1]?.focus();
    else if (e.key === 'ArrowRight' && i < LENGTH - 1) refs.current[i + 1]?.focus();
  }

  function handlePaste(e) {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, LENGTH);
    if (!pasted) return;
    e.preventDefault();
    commit(pasted);
    refs.current[Math.min(pasted.length, LENGTH - 1)]?.focus();
  }

  return (
    <div className="otp" role="group" aria-labelledby={`${groupId}-label`}>
      <span id={`${groupId}-label`} className="sr-only">
        Six-digit verification code
      </span>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => (refs.current[i] = el)}
          className={`otp__box ${error ? 'otp__box--error' : ''}`}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={LENGTH}
          value={d}
          disabled={disabled}
          aria-label={`Digit ${i + 1} of ${LENGTH}`}
          aria-invalid={error ? 'true' : undefined}
          onChange={(e) => handleChange(i, e)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
        />
      ))}
    </div>
  );
}
