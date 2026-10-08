from ultralytics import YOLO
import numpy as np

# Load the trained model globally to avoid reloading it multiple times
model = YOLO('runs/train/yolo_food_training/weights/best.pt')

def predict_image(image_path, class_names):
    """
    Predict the class of a food item in an image.

    Args:
        image_path (str): Path to the input image.
        class_names (list): List of food class names.

    Returns:
        str: Predicted class name.
    """
    # Run inference
    results = model(image_path)
    
    # Parse predictions
    for result in results:
        # Access the detection labels (index-based)
        if result.boxes:
            labels = result.boxes.cls.cpu().numpy()  # Get class indices
            if len(labels) > 0:
                # Return the first detected class name
                return class_names[int(labels[0])]
    return "Unknown"
