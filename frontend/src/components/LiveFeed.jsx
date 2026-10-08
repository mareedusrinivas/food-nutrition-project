import { useState } from 'react';
import { FiVideo, FiVideoOff } from 'react-icons/fi';
import { liveFeedUrl } from '../services/api.js';

/**
 * LiveFeed — the MJPEG camera stream (<img src="/live_feed">) from
 * templates/index.html, plus loading/error states for the stream itself.
 */
export default function LiveFeed() {
  const [status, setStatus] = useState('loading'); // loading | ready | error

  return (
    <div className="live-feed">
      {status === 'loading' && (
        <div className="live-feed__placeholder" role="status">
          <FiVideo className="spin" aria-hidden="true" />
          <p>Connecting to camera…</p>
        </div>
      )}
      {status === 'error' && (
        <div className="live-feed__placeholder live-feed__placeholder--error" role="alert">
          <FiVideoOff aria-hidden="true" />
          <p>Camera feed unavailable. Is the backend running?</p>
        </div>
      )}
      <img
        src={liveFeedUrl}
        id="video-feed"
        alt="Live camera feed showing the food in front of the camera"
        onLoad={() => setStatus('ready')}
        onError={() => setStatus('error')}
        style={{ display: status === 'ready' ? 'block' : 'none' }}
      />
    </div>
  );
}
