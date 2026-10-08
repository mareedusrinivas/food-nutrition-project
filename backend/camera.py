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

import os
import sys
import threading
import time

import cv2


def _silence_opencv_logs():
    """Keep OpenCV from flooding the console when no camera is present.

    Without a device, every ``VideoCapture`` attempt prints several WARN/ERROR
    lines through OpenCV's own logger (which bypasses Python logging). We cap
    its verbosity and additionally redirect C-level stderr while probing so
    startup stays clean; normal operation with a real camera is unaffected.
    """
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
        cv2.utils.logging.setVerbosity(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        pass


class Camera:
    def __init__(self, source=0, jpeg_quality=80, retry_seconds=15.0):
        self.source = source
        self.jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
        self.retry_seconds = float(retry_seconds)
        self._lock = threading.Lock()
        self._frame = None          # latest raw frame (for capture)
        self._jpeg = None           # latest frame, JPEG-encoded once
        self._counter = 0           # incremented for every new frame
        self._thread = None
        self._running = False
        self.available = False      # True once a real frame has been grabbed
        self.open_failures = 0      # consecutive failed open attempts

    # ------------------------------------------------------------------ life
    def start(self):
        if self._thread is not None:
            return
        _silence_opencv_logs()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    # ------------------------------------------------------------- internals
    @staticmethod
    def _quiet_stderr():
        """Context manager suppressing C-level stderr (OpenCV's logger writes
        there directly, so Python-side redirection cannot catch it)."""

        class _Suppress:
            def __enter__(self):
                self.devnull = open(os.devnull, 'w')
                self.saved = os.dup(2)
                sys.stderr.flush()
                os.dup2(self.devnull.fileno(), 2)
                return self

            def __exit__(self, *exc):
                try:
                    sys.stderr.flush()
                    os.dup2(self.saved, 2)
                finally:
                    os.close(self.saved)
                    self.devnull.close()

        return _Suppress()

    def _open_capture(self):
        with self._quiet_stderr():
            cap = cv2.VideoCapture(self.source)
        if cap.isOpened():
            # Keep grab latency low: small buffer, lower resolution.
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            except Exception:
                pass
        else:
            cap.release()
            cap = None
        return cap

    def _run(self):
        first_try = True
        cap = self._open_capture()
        while self._running:
            if cap is None:
                # No camera present (or unplugged/busy): back off exponentially
                # instead of hammering VideoCapture every second, which floods
                # the console with OpenCV warnings on machines without a webcam.
                delay = min(self.retry_seconds, 1.0 * (2 ** min(self.open_failures, 4)))
                if first_try:
                    first_try = False
                    print("[camera] WARNING: no camera found at source "
                          f"{self.source!r}. The live feed will show a "
                          "'no camera' placeholder and capture returns an "
                          f"error. Re-checking every ~{delay:.0f}s. "
                          "(Set CAMERA_SOURCE=<index|video-file-url> to use "
                          "a different device.)", file=sys.stderr, flush=True)
                self.open_failures += 1
                self.available = False
                time.sleep(delay)
                cap = self._open_capture()
                continue
            if not self.available:
                self.available = True
                self.open_failures = 0
                print(f"[camera] Camera ready (source {self.source}).",
                      file=sys.stderr, flush=True)
            ok, frame = cap.read()
            if not ok:
                # Video files end; loop them so the feed keeps playing.
                if isinstance(self.source, str):
                    try:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    except Exception:
                        pass
                cap.release()
                cap = None
                self.available = False
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

    def _placeholder_jpeg(self):
        """Dark 'No camera detected' frame so the live feed never stalls."""
        import numpy as np
        img = np.zeros((480, 640, 3), dtype='uint8')
        img[:] = (24, 24, 28)
        cv2.putText(img, 'No camera detected', (150, 235),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (170, 170, 170), 2)
        cv2.putText(img, 'Connect a webcam or set CAMERA_SOURCE', (105, 275),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 120), 1)
        ok, buf = cv2.imencode('.jpg', img, self.jpeg_params)
        return buf.tobytes() if ok else None

    def stream(self):
        """Generator yielding multipart MJPEG chunks for one client."""
        last_counter = -1
        idle_since = time.monotonic()
        while self._running:
            with self._lock:
                counter, jpeg = self._counter, self._jpeg
            if counter != last_counter and jpeg is not None:
                last_counter = counter
                idle_since = time.monotonic()
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + jpeg + b'\r\n')
            else:
                # If no real frames have flowed for a while (camera missing),
                # send a placeholder so browsers show a helpful message and
                # the <img> keeps reporting the stream as alive.
                if time.monotonic() - idle_since > 2.0:
                    placeholder = self._placeholder_jpeg()
                    if placeholder is not None:
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                               + placeholder + b'\r\n')
                    idle_since = time.monotonic() - 1.0  # ~1 Hz placeholders
                time.sleep(0.05)
