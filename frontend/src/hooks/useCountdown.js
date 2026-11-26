import { useEffect, useState } from 'react';

/** Seconds remaining until `targetMs` (epoch ms). Re-renders every 250 ms; derived from the clock, so tab throttling can't drift it. */
export function useCountdown(targetMs) {
  const calc = () => (targetMs ? Math.max(0, Math.ceil((targetMs - Date.now()) / 1000)) : 0);
  const [remaining, setRemaining] = useState(calc);

  useEffect(() => {
    setRemaining(calc());
    if (!targetMs) return undefined;
    const id = setInterval(() => {
      const next = Math.max(0, Math.ceil((targetMs - Date.now()) / 1000));
      setRemaining(next);
      if (next === 0) clearInterval(id);
    }, 250);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetMs]);

  return remaining;
}
