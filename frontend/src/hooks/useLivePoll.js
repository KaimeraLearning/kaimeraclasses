import { useEffect, useRef } from 'react';

/**
 * useLivePoll — calls `fn` on a regular interval while the tab is visible.
 *
 * - Default interval: 15 seconds.
 * - Pauses while document.visibilityState !== 'visible' (saves bandwidth/server load).
 * - Resumes immediately when tab becomes visible again (with a fresh fetch).
 * - Always reads the latest fn via a ref so callers don't have to memoize it.
 */
export function useLivePoll(fn, intervalMs = 15000, deps = []) {
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  useEffect(() => {
    let timer = null;
    const tick = () => {
      if (document.visibilityState === 'visible') {
        try { fnRef.current && fnRef.current(); } catch {}
      }
    };
    timer = setInterval(tick, intervalMs);
    const onVis = () => {
      if (document.visibilityState === 'visible') {
        try { fnRef.current && fnRef.current(); } catch {}
      }
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      if (timer) clearInterval(timer);
      document.removeEventListener('visibilitychange', onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);
}
