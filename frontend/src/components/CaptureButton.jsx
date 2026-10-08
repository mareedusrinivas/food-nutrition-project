import { FiLoader } from 'react-icons/fi';

/**
 * CaptureButton — the "Capture Image" button from templates/index.html.
 * Shows a spinner while a capture is in flight; text stays "Capture Image".
 */
export default function CaptureButton({ onCapture, processing }) {
  return (
    <button
      id="capture-button"
      type="button"
      className="capture-button"
      onClick={onCapture}
      disabled={processing}
      aria-busy={processing}
    >
      {processing && <FiLoader className="spin" aria-hidden="true" />}
      Capture Image
      {/* live region so screen readers announce the processing state */}
      <span className="sr-only" role="status">
        {processing ? 'Capturing and analyzing image' : ''}
      </span>
    </button>
  );
}
