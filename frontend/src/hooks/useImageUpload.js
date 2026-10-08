import { useCallback, useEffect, useRef, useState } from 'react';
import { uploadImage } from '../services/api.js';

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // keep in sync with backend limit
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];

/**
 * useImageUpload — encapsulates the "upload a food photo" flow:
 * client-side validation (type/size), object-URL preview management,
 * and the POST /api/upload request with loading/error state.
 *
 * Returns { file, previewUrl, selectFile, clearFile, analyze, processing, error, clearError }.
 * `analyze()` resolves with the payload ({ prediction, image, calories, … })
 * or returns null on failure (the error is surfaced inline via `error`).
 */
export default function useImageUpload() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const abortRef = useRef(null);
  const urlRef = useRef('');

  // Revoke object URLs / abort requests when this hook unmounts.
  useEffect(() => () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    abortRef.current?.abort();
  }, []);

  const clearFile = useCallback(() => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = '';
    setFile(null);
    setPreviewUrl('');
  }, []);

  /** Validate + accept a File. Returns true if it was accepted. */
  const selectFile = useCallback((next) => {
    setError('');
    if (!next) return false;

    if (!ACCEPTED_TYPES.includes(next.type)) {
      setError('Please choose an image file (JPG, PNG, WEBP or BMP).');
      return false;
    }
    if (next.size > MAX_SIZE_BYTES) {
      setError('Image too large (max 10 MB). Please choose a smaller photo.');
      return false;
    }

    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    const url = URL.createObjectURL(next);
    urlRef.current = url;
    setFile(next);
    setPreviewUrl(url);
    return true;
  }, []);

  /** Upload the selected file and run analysis on the server. */
  const analyze = useCallback(async () => {
    if (!file) {
      setError('Please choose an image first.');
      return null;
    }
    setProcessing(true);
    setError('');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      return await uploadImage(file, controller.signal);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Error uploading image:', err);
        setError(err.message || 'Failed to analyze the image. Please try again.');
      }
      return null;
    } finally {
      setProcessing(false);
    }
  }, [file]);

  const clearError = useCallback(() => setError(''), []);

  return {
    file, previewUrl, selectFile, clearFile,
    analyze, processing, error, clearError,
  };
}
