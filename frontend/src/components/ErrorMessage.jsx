import { useState } from 'react';
import { FiAlertTriangle, FiX } from 'react-icons/fi';

/**
 * ErrorMessage — dismissible inline error banner used when a capture fails.
 * Replaces the old `alert("Failed to capture image…")` from static/js/script.js
 * with a non-blocking, accessible message.
 */
export default function ErrorMessage({ message, onDismiss }) {
  const [visible, setVisible] = useState(true);

  if (!message || !visible) return null;

  return (
    <div className="error-banner" role="alert">
      <FiAlertTriangle aria-hidden="true" />
      <span>{message}</span>
      <button
        type="button"
        className="error-banner__dismiss"
        aria-label="Dismiss error"
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
      >
        <FiX aria-hidden="true" />
      </button>
    </div>
  );
}
