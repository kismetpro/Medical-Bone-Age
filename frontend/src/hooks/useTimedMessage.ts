import { useCallback, useEffect, useRef, useState } from 'react';

export interface TimedMessage {
  type: 'success' | 'error';
  text: string;
}

export function useTimedMessage(duration = 3000) {
  const [message, setMessage] = useState<TimedMessage | null>(null);
  const timerRef = useRef<number | null>(null);

  const clearMessage = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setMessage(null);
  }, []);

  const showMessage = useCallback(
    (type: TimedMessage['type'], text: string) => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }

      setMessage({ type, text });
      timerRef.current = window.setTimeout(() => {
        setMessage(null);
        timerRef.current = null;
      }, duration);
    },
    [duration],
  );

  useEffect(() => () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
    }
  }, []);

  return {
    message,
    showMessage,
    clearMessage,
  };
}
