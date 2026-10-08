import os
import time

import cv2
import numpy as np
from flask import (Flask, request, render_template, Response, redirect,
                   url_for, jsonify, send_from_directory)

from camera import Camera
from nutrition import NutritionClient
from scripts.infer import predict_image

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Let browsers/CDNs cache the static React bundle & uploaded images briefly.
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300
# Accept uploads up to 20 MB at the Flask layer (we enforce a friendlier
# 10 MB limit with a clear JSON message inside _read_upload).
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

class_names = ['Apple', 'Chapati', 'Chicken Gravy', 'Fries', 'Idli', 'Pizza', 'Rice', 'Soda', 'Tomato', 'Vada', 'Banana', 'Hamburger']

USDA_API_KEY = os.environ.get("USDA_API_KEY", "lw9DCn2bR0LvcVyjZGFqDchc3CURiSIMd5t5vzxw")

# The app is image-upload driven by default — NO webcam is opened unless the
# user explicitly opts in with ENABLE_CAMERA=1. When disabled we skip creating
# the Camera object entirely, so there are zero OpenCV camera warnings/errors
# in the console on machines without (or with an ignored) webcam.
# CAMERA_SOURCE can be a webcam index (0, 1, ...) or a video-file/stream URL.
ENABLE_CAMERA = os.environ.get("ENABLE_CAMERA", "0").lower() in ("1", "true", "yes", "on")
camera = None
if ENABLE_CAMERA:
    _cam_source = os.environ.get("CAMERA_SOURCE", "0")
    try:
        _cam_source = int(_cam_source)
    except ValueError:
        pass  # treat as file path / stream URL
    camera = Camera(source=_cam_source)
    camera.start()

# USDA lookups are cached per food name; repeated captures of the same food
# return instantly instead of making an external HTTP call every time.
nutrition_client = NutritionClient(USDA_API_KEY)


def run_capture(frame=None):
    """Classify a frame and look up nutrition data.

    ``frame`` is a BGR numpy array — from an uploaded image (the default
    upload-only flow) or, when ENABLE_CAMERA=1, the latest camera frame.
    The frame is fed directly to the model as a numpy array — the previous
    flow wrote a JPEG to disk and read it back inside YOLO, adding
    unnecessary I/O latency to every capture. The snapshot is saved after
    the slow prediction so the result page has a stable image URL.

    Returns (payload_dict, error_message).
    """
    if frame is None:
        frame = camera.current_frame if camera is not None else None
    if frame is None:
        return None, ("No image received — please upload a photo of the food.")

    try:
        t0 = time.perf_counter()
        prediction = predict_image(frame, class_names)      # in-memory inference
        infer_ms = (time.perf_counter() - t0) * 1000

        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_image.jpg')
        # Save at reduced quality: smaller file => faster browser download.
        cv2.imwrite(image_path, frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        t1 = time.perf_counter()
        nutrition = nutrition_client.fetch(prediction)       # cached USDA lookup
        usda_ms = (time.perf_counter() - t1) * 1000

        app.logger.info("capture: %s | inference %.0f ms, usda %.0f ms",
                        prediction, infer_ms, usda_ms)

        return {
            "prediction": prediction,
            "image": image_path,
            "calories": nutrition['calories'],
            "carbohydrates": nutrition['carbohydrates'],
            "protein": nutrition['protein'],
            "fat": nutrition['fat'],
            "fiber": nutrition['fiber'],
            "sugar": nutrition['sugar'],
        }, None
    except Exception as e:
        app.logger.exception("Error during capture")
        return None, f"Error during capture: {str(e)}"


# Live Camera Feed — MJPEG stream (only when ENABLE_CAMERA=1). When camera
# mode is off the frontend never requests this; we still answer with a plain
# 503 instead of hanging on an empty stream.
@app.route('/live_feed')
def live_feed():
    if camera is None:
        return jsonify({"error": "Camera is disabled. Upload an image instead "
                                 "(or start the backend with ENABLE_CAMERA=1)."}), 503
    return Response(camera.stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _read_upload():
    """Decode the multipart 'image' file into a BGR numpy array.

    Returns (frame, error_message). Uses np.frombuffer + cv2.imdecode so any
    format OpenCV understands (jpg/png/webp/bmp…) works, without trusting the
    client-supplied MIME type or filename.
    """
    file = request.files.get('image')
    if file is None or file.filename == '':
        return None, "No image uploaded. Please choose a photo of the food."

    raw = file.read(MAX_UPLOAD_BYTES + 1)
    if not raw:
        return None, "The uploaded file is empty."
    if len(raw) > MAX_UPLOAD_BYTES:
        return None, "Image too large (max 10 MB). Please choose a smaller photo."

    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None, "Could not read that file as an image. Please upload a JPG/PNG photo."

    # Downscale very large photos before inference: faster YOLO pass and
    # smaller saved snapshot, with no accuracy impact at these sizes.
    h, w = frame.shape[:2]
    max_side = 1280
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)
    return frame, None


# JSON API for the React frontend: upload a food photo -> prediction + nutrition.
# This is the primary flow; the camera is opt-in (ENABLE_CAMERA=1).
@app.route('/api/upload', methods=['POST'])
def api_upload():
    frame, error = _read_upload()
    if error:
        return jsonify({"error": error}), 400
    payload, error = run_capture(frame)
    if error:
        status = 500 if error.startswith("Error") else 400
        return jsonify({"error": error}), status
    return jsonify(payload)


# JSON API for the React frontend (camera mode only)
# Previously this redirected to the Flask-rendered /result page; now it
# returns the prediction + nutrition data as JSON so React can navigate
# to its own /result route.
@app.route('/api/capture', methods=['POST'])
def api_capture():
    if camera is None:
        return jsonify({"error": "Camera is disabled — upload an image instead."}), 503
    payload, error = run_capture()
    if error:
        status = 500 if error.startswith("Error") else 503
        return jsonify({"error": error}), status
    return jsonify(payload)


# Legacy endpoint kept for backwards compatibility with the old
# static/js/script.js flow (redirect-based). Accepts an optional uploaded
# 'image' file; falls back to the camera frame when camera mode is enabled.
@app.route('/capture', methods=['POST'])
def capture():
    frame, error = (None, None)
    if request.files.get('image'):
        frame, error = _read_upload()
        if error:
            return jsonify({"error": error}), 400
    payload, error = run_capture(frame)
    if error:
        status = 500 if error.startswith("Error") else 503
        return jsonify({"error": error}), status
    return redirect(url_for('result', **payload))


# Serve the built React app (frontend/dist) so Flask can host the SPA in production
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             '..', 'frontend', 'dist'))


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIST, 'index.html', max_age=300)


@app.route('/<path:path>')
def serve_frontend(path):
    # Serve static assets from the React build; fall back to index.html for client-side routes
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.isfile(file_path):
        # Hashed Vite assets (…-abc123.js) are immutable → cache them hard.
        age = 86400 * 365 if '-tmp-' not in path and _is_hashed_asset(path) else 300
        return send_from_directory(FRONTEND_DIST, path, max_age=age)
    return send_from_directory(FRONTEND_DIST, 'index.html', max_age=0)


def _is_hashed_asset(path):
    """True for Vite production assets like /assets/index-D4Gf9xkQ.js.

    Vite content-hashes bundled filenames as ``<name>-<hash>.<ext>`` where the
    hash is an 8-character base64url string (alphabet: A-Z a-z 0-9 - _). The
    hash may itself contain dashes/underscores (e.g. ``index-C-_trZlc.js``,
    ``back1-DEKfdh_c.jpeg``), so we test every dash split point and require:
      * the suffix after the dash is exactly 8 hash-alphabet characters with
        at least one digit or uppercase letter, AND
      * the prefix before the dash contains no other lowercase alphabetic
        word segment (real bundle names are single tokens like ``index`` or
        ``back5``; prose-like names such as ``some-old-file`` are rejected).
    Misclassification is safe either way — it only changes Cache-Control
    max-age, never correctness.
    """
    name = os.path.basename(path)
    if '.' not in name or '-' not in name:
        return False
    stem = name.rsplit('.', 1)[0]
    for i, ch in enumerate(stem):
        if ch != '-':
            continue
        prefix, tail = stem[:i], stem[i + 1:]
        if not prefix or prefix.endswith('-') or _has_word_segment(prefix):
            continue
        if _looks_hashed(tail):
            return True
    return False


def _looks_hashed(tail):
    """Whether ``tail`` looks like an 8-char Vite content hash."""
    return (len(tail) == 8
            and set(tail).issubset(_HASH_CHARS)
            and any(not c.islower() for c in tail))


def _has_word_segment(s):
    """True if any dash-separated part of ``s`` is a pure lowercase word."""
    return any(p.isalpha() and p.islower() for p in s.split('-'))


_HASH_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')


# Fetch Nutrition Data (legacy Flask-rendered page, superseded by the React Result page)
@app.route('/result')
def result():
    prediction = request.args.get('prediction', 'Unknown')
    image_path = request.args.get('image', '')
    calories = request.args.get('calories', 'N/A')
    carbohydrates = request.args.get('carbohydrates', 'N/A')
    protein = request.args.get('protein', 'N/A')
    fat = request.args.get('fat', 'N/A')
    fiber = request.args.get('fiber', 'N/A')
    sugar = request.args.get('sugar', 'N/A')

    return render_template('result.html', prediction=prediction, image_path=image_path,
                           calories=calories, carbohydrates=carbohydrates, protein=protein,
                           fat=fat, fiber=fiber, sugar=sugar)


if __name__ == '__main__':
    # debug=True keeps auto-reload for development; threaded=True lets the
    # MJPEG stream hold a connection without blocking other requests.
    app.run(debug=bool(int(os.environ.get("FLASK_DEBUG", "1"))),
            threaded=True,
            use_reloader=False)
