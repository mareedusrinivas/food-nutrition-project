import os
import time

import cv2
from flask import Flask, request, render_template, Response, redirect, url_for, jsonify, send_from_directory

from camera import Camera
from nutrition import NutritionClient
from scripts.infer import predict_image

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Let browsers/CDNs cache the static React bundle & uploaded images briefly.
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300

class_names = ['Apple', 'Chapati', 'Chicken Gravy', 'Fries', 'Idli', 'Pizza', 'Rice', 'Soda', 'Tomato', 'Vada', 'Banana', 'Hamburger']

USDA_API_KEY = os.environ.get("USDA_API_KEY", "lw9DCn2bR0LvcVyjZGFqDchc3CURiSIMd5t5vzxw")

# One shared camera instance: a background thread reads + JPEG-encodes frames
# once, so /live_feed no longer reopens the device or re-encodes per client,
# and /api/capture never blocks waiting for a grab.
camera = Camera(source=int(os.environ.get("CAMERA_SOURCE", "0")))
camera.start()

# USDA lookups are cached per food name; repeated captures of the same food
# return instantly instead of making an external HTTP call every time.
nutrition_client = NutritionClient(USDA_API_KEY)


def run_capture():
    """Grab the latest frame, classify it, and look up nutrition data.

    Returns (payload_dict, error_message). The frame is fed directly to the
    model as a numpy array — the previous flow wrote a JPEG to disk and read
    it back inside YOLO, adding unnecessary I/O latency to every capture.
    The snapshot is still saved asynchronously-ish (cheap imwrite after the
    slow prediction) so the result page has a stable image URL.
    """
    frame = camera.current_frame
    if frame is None:
        return None, "No frame to capture"

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


# Live Camera Feed — MJPEG stream served from the shared encoded frames.
@app.route('/live_feed')
def live_feed():
    return Response(camera.stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# JSON API for the React frontend (frontend/src/components/LiveFeed.jsx)
# Previously this redirected to the Flask-rendered /result page; now it
# returns the prediction + nutrition data as JSON so React can navigate
# to its own /result route.
@app.route('/api/capture', methods=['POST'])
def api_capture():
    payload, error = run_capture()
    if error:
        status = 500 if error.startswith("Error") else 503
        return jsonify({"error": error}), status
    return jsonify(payload)


# Legacy endpoint kept for backwards compatibility with the old
# static/js/script.js flow (redirect-based). The React app uses /api/capture.
@app.route('/capture', methods=['POST'])
def capture():
    payload, error = run_capture()
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
