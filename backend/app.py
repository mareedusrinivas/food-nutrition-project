import os
import cv2
import requests
from flask import Flask, request, render_template, Response, redirect, url_for, jsonify, send_from_directory
from scripts.infer import predict_image

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class_names = ['Apple', 'Chapati', 'Chicken Gravy', 'Fries', 'Idli', 'Pizza', 'Rice', 'Soda', 'Tomato', 'Vada', 'Banana', 'Hamburger']

USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_API_KEY = os.environ.get("USDA_API_KEY", "lw9DCn2bR0LvcVyjZGFqDchc3CURiSIMd5t5vzxw")
current_frame = None

# Live Camera Feed
@app.route('/live_feed')
def live_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def generate_frames():
    global current_frame
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        current_frame = frame
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()


# JSON API for the React frontend (frontend/src/components/LiveFeed.jsx)
# Previously this redirected to the Flask-rendered /result page; now it
# returns the prediction + nutrition data as JSON so React can navigate
# to its own /result route.
@app.route('/api/capture', methods=['POST'])
def api_capture():
    global current_frame
    if current_frame is not None:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_image.jpg')
            cv2.imwrite(image_path, current_frame)
            prediction = predict_image(image_path, class_names)
            nutrition = fetch_nutrition(prediction)

            return jsonify({
                "prediction": prediction,
                "image": image_path,
                "calories": nutrition['calories'],
                "carbohydrates": nutrition['carbohydrates'],
                "protein": nutrition['protein'],
                "fat": nutrition['fat'],
                "fiber": nutrition['fiber'],
                "sugar": nutrition['sugar'],
            })
        except Exception as e:
            print(f"Error during capture: {e}")
            return jsonify({"error": f"Error during capture: {str(e)}"}), 500
    return jsonify({"error": "No frame to capture"}), 500


# Legacy endpoint kept for backwards compatibility with the old
# static/js/script.js flow (redirect-based). The React app uses /api/capture.
@app.route('/capture', methods=['POST'])
def capture():
    global current_frame
    if current_frame is not None:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_image.jpg')
            cv2.imwrite(image_path, current_frame)
            prediction = predict_image(image_path, class_names)
            nutrition = fetch_nutrition(prediction)

            # Return the response with prediction and nutrition data
            return redirect(url_for('result', prediction=prediction, image=image_path,
                                    calories=nutrition['calories'], carbohydrates=nutrition['carbohydrates'],
                                    protein=nutrition['protein'], fat=nutrition['fat'], fiber=nutrition['fiber'],
                                    sugar=nutrition['sugar']))
        except Exception as e:
            print(f"Error during capture: {e}")
            return jsonify({"error": f"Error during capture: {str(e)}"}), 500
    return jsonify({"error": "No frame to capture"}), 500


# Serve the built React app (frontend/dist) so Flask can host the SPA in production
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/<path:path>')
def serve_frontend(path):
    # Serve static assets from the React build; fall back to index.html for client-side routes
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, 'index.html')


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


def fetch_nutrition(food_item):
    params = {"query": food_item, "api_key": USDA_API_KEY}
    response = requests.get(USDA_API_URL, params=params).json()
    
    if response.get('foods'):
        nutrients = response['foods'][0].get('foodNutrients', [])
        return {
            "calories": extract_nutrient(nutrients, "Energy"),
            "carbohydrates": extract_nutrient(nutrients, "Carbohydrate, by difference"),
            "protein": extract_nutrient(nutrients, "Protein"),
            "fat": extract_nutrient(nutrients, "Total lipid (fat)"),
            "fiber": extract_nutrient(nutrients, "Fiber, total dietary"),
            "sugar": extract_nutrient(nutrients, "Sugars, total including NLEA")
        }
    return {"calories": "N/A", "carbohydrates": "N/A", "protein": "N/A", "fat": "N/A", "fiber": "N/A", "sugar": "N/A"}


def extract_nutrient(nutrients, nutrient_name):
    for nutrient in nutrients:
        if nutrient["nutrientName"] == nutrient_name:
            return nutrient["value"]
    return "N/A"


if __name__ == '__main__':
    app.run(debug=True)
