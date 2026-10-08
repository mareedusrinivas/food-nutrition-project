from ultralytics import YOLO

# Load the trained model
model = YOLO('runs/train/yolo_food_training/weights/best.pt')

# Evaluate model
metrics = model.val()

# Print evaluation metrics
print("Evaluation metrics:")
for key, value in metrics.items():
    print(f"{key}: {value}")
