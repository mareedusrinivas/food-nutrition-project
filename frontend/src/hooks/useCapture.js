import { useCallback, useEffect, useRef, useState } from 'react';
import { captureImage } from '../services/api.js';

/**
 * useCapture — encapsulates the "Capture Image" flow that previously lived
 * in backend/static/js/script.js (fetch /capture + button disable/re-enable).
 *
 * Returns { capture, processing, error, clearError }.
 * `capture()` resolves with the payload produced by the backend
 * ({ prediction, image, calories, … }) or returns null on failure.
 */
export default function useCapture() {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const abortRef = useRef(null);

  // Abort any in-flight request when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const capture = useCallback(async () => {
    setProcessing(true);
    setError('');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      return await captureImage(controller.signal);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Error capturing image:', err);
        setError(err.message || 'Failed to capture image. Please try again.');
      }
      return null;
    } finally {
      setProcessing(false);
    }
  }, []);

  const clearError = useCallback(() => setError(''), []);

  return { capture, processing, error, clearError };
}
