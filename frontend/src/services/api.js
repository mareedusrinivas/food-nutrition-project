// Thin API/service layer over the Flask backend (backend/app.py).
//
// The backend origin can be overridden with VITE_API_URL (see .env.example);
// when it is empty we use relative URLs and rely on the Vite dev-server proxy
// (frontend/vite.config.js) or on Flask serving the built SPA in production.
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}

/**
 * POST /api/upload — upload a food photo (multipart 'image' file); the
 * server runs YOLO classification + the USDA nutrition lookup on it.
 * This is the primary flow of the app (no webcam required).
 * Resolves with:
 *   { prediction, image, calories, carbohydrates, protein, fat, fiber, sugar }
 */
export async function uploadImage(file, signal) {
  const formData = new FormData();
  formData.append('image', file);

  const response = await fetch(apiUrl('/api/upload'), {
    method: 'POST',
    body: formData,
    signal,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* non-JSON error body — fall through to the status check below */
  }

  if (!response.ok) {
    throw new Error(
      data?.error || `Server responded with status: ${response.status}`,
    );
  }
  if (data?.error) {
    throw new Error(data.error);
  }
  return data;
}

/**
 * POST /api/capture — grab the latest camera frame (camera mode only;
 * requires the backend to run with ENABLE_CAMERA=1).
 */
export async function captureImage(signal) {
  const response = await fetch(apiUrl('/api/capture'), {
    method: 'POST',
    signal,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* non-JSON error body — fall through to the status check below */
  }

  if (!response.ok) {
    throw new Error(
      data?.error || `Server responded with status: ${response.status}`,
    );
  }
  if (data?.error) {
    throw new Error(data.error);
  }
  return data;
}

/** Absolute URL of the MJPEG live camera stream (Flask `/live_feed`). */
export const liveFeedUrl = apiUrl('/live_feed');

/**
 * Resolve an image path returned by the backend (e.g. "static/uploads/…")
 * into a URL the browser can load. Uploaded images are served by Flask;
 * unknown paths are passed through unchanged so absolute URLs still work.
 */
export function resolveImageUrl(imagePath) {
  if (!imagePath) return '';
  const clean = String(imagePath).replace(/^(\.\.?\/|\/)+/, '');
  return apiUrl(`/${clean}`);
}
