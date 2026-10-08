# train.py
from ultralytics import YOLO

# Load YOLOv8 model
model = YOLO('yolov8n.pt')  # Replace 'yolov8n.pt' with a larger variant if needed

# Train model
model.train(
    data="data.yaml",        # Path to data.yaml
    epochs=50,               # Numbers sof epochs
    imgsz=640,               # Image size
    batch=16,                # Batch size
    name='yolo_food_training' # Name of the training experiment
)

print("Training completed. Best model saved to: runs/train/yolo_food_training/weights/best.pt")

