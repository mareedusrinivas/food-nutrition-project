import { FiLoader } from 'react-icons/fi';

/**
 * CaptureButton — the primary action button ("Analyze Image" in upload mode,
 * "Capture Image" in camera mode). Shows a spinner while a request is in
 * flight; kept as one reusable component for both flows.
 */
export default function CaptureButton({ onCapture, processing, label = 'Capture Image' }) {
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
      {label}
      {/* live region so screen readers announce the processing state */}
      <span className="sr-only" role="status">
        {processing ? 'Analyzing image, please wait' : ''}
      </span>
    </button>
  );
}
