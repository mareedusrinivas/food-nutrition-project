import os
import threading

import numpy as np
from ultralytics import YOLO

# Absolute default model path so inference works regardless of the CWD the
# server was launched from (previously a relative path, which forced loading
# to fail/reload when run from outside backend/).
_MODEL_PATH = os.environ.get(
    'YOLO_MODEL_PATH',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'runs', 'train', 'yolo_food_training', 'weights', 'best.pt'),
)

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Return the globally cached YOLO model, loading it exactly once.

    Lazy loading keeps app start-up fast; the singleton avoids reloading the
    weights on every prediction. Inference is serialized with a lock because
    the Ultralytics predictor holds mutable internal state and is not
    thread-safe.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = YOLO(_MODEL_PATH)
    return _model


def predict_image(image_path, class_names):
    """
    Predict the class of a food item in an image.

    Args:
        image_path (str): Path to the input image, or a raw numpy BGR frame.
        class_names (list): List of food class names.

    Returns:
        str: Predicted class name.
    """
    model = _get_model()

    # Run inference (no disk round-trip needed when given a numpy array).
    results = model.predict(image_path, verbose=False)

    # Parse predictions
    for result in results:
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            labels = boxes.cls.cpu().numpy()   # class indices
            confs = boxes.conf.cpu().numpy()   # confidence scores
            # Return the highest-confidence detection rather than whichever
            # box happened to be listed first.
            best = int(np.argmax(confs))
            return class_names[int(labels[best])]
    return "Unknown"
