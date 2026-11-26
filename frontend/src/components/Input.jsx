import { forwardRef, useId } from 'react';

const Input = forwardRef(function Input({ label, error, hint, id, className = '', ...rest }, ref) {
  const auto = useId();
  const inputId = id || auto;
  const describedBy = [error && `${inputId}-error`, hint && `${inputId}-hint`].filter(Boolean).join(' ') || undefined;
  return (
    <div className={`field ${error ? 'field--error' : ''} ${className}`}>
      <label className="field__label" htmlFor={inputId}>
        {label}
      </label>
      <input ref={ref} id={inputId} className="field__input" aria-invalid={error ? 'true' : undefined} aria-describedby={describedBy} {...rest} />
      {hint && !error && (
        <p className="field__hint" id={`${inputId}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field__error" id={`${inputId}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
});

export default Input;
