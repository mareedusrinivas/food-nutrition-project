"""Threaded camera reader for the live MJPEG feed.

Performance notes:
- A single background thread owns the ``cv2.VideoCapture`` and continuously
  reads frames, so HTTP requests never block on camera I/O and the camera
  device is opened only once (reopening per request was slow and leaked
  devices when clients disconnected).
- JPEG encoding happens exactly once per frame in the reader thread; all
  streaming clients share the same encoded bytes instead of re-encoding the
  raw frame on every response iteration.
- Thread-safe access to the shared frame via a lock; stale clients simply
  wait for the next frame counter increment.
"""

import threading
import time

import cv2


class Camera:
    def __init__(self, source=0, jpeg_quality=80):
        self.source = source
        self.jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
        self._lock = threading.Lock()
        self._frame = None          # latest raw frame (for capture)
        self._jpeg = None           # latest frame, JPEG-encoded once
        self._counter = 0           # incremented for every new frame
        self._thread = None
        self._running = False

    # ------------------------------------------------------------------ life
    def start(self):
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    # ------------------------------------------------------------- internals
    def _open_capture(self):
        cap = cv2.VideoCapture(self.source)
        if cap.isOpened():
            # Keep grab latency low: small buffer, lower resolution.
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            except Exception:
                pass
        return cap

    def _run(self):
        cap = self._open_capture()
        while self._running:
            if cap is None or not cap.isOpened():
                # Device unplugged / busy — retry periodically instead of dying.
                time.sleep(1.0)
                cap = self._open_capture()
                continue
            ok, frame = cap.read()
            if not ok:
                cap.release()
                cap = None
                continue
            # Encode once; every client consumes the same bytes.
            ok, buf = cv2.imencode('.jpg', frame, self.jpeg_params)
            if not ok:
                continue
            with self._lock:
                self._frame = frame
                self._jpeg = buf.tobytes()
                self._counter += 1

    # ----------------------------------------------------------------- public
    @property
    def current_frame(self):
        """Latest raw frame (numpy BGR array) or None."""
        with self._lock:
            return self._frame

    def stream(self):
        """Generator yielding multipart MJPEG chunks for one client."""
        last_counter = -1
        while self._running:
            with self._lock:
                counter, jpeg = self._counter, self._jpeg
            if counter != last_counter and jpeg is not None:
                last_counter = counter
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + jpeg + b'\r\n')
            else:
                time.sleep(0.01)
