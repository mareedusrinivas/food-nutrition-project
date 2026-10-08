# Live Food Detection & Calorimetry (React + Flask)

The project is split into two independent parts:

```
.
├── frontend/          # React (Vite) single-page app  — all UI
│   ├── src/
│   │   ├── pages/        Home.jsx (camera feed + capture), Result.jsx (nutrition card)
│   │   ├── components/   LiveFeed.jsx
│   │   └── App.jsx       React Router routes (/ and /result)
│   └── vite.config.js    Dev-server proxy to the Flask backend
├── backend/           # Flask API + YOLO model + IoT assets
│   ├── app.py            REST endpoints (/api/capture, /live_feed, …)
│   ├── scripts/          train.py / infer.py / evaluation.py
│   ├── data.yaml         YOLO dataset config
│   ├── yolov8n.pt        Model weights
│   ├── dataset/ runs/ inference_results/
│   ├── static/ templates/  Legacy Flask assets (kept for backwards compatibility)
│   ├── iot-related files live in ../iot (ESP32 firmware)
│   └── requirements.txt
└── iot/               # ESP32 / Arduino firmware
```

## Run everything with one command

From the repository root:

```bash
python run.py            # dev mode: Flask :5000 + Vite React dev server :5173
python run.py --build    # production mode: builds React app, Flask serves it at :5000
```

`run.py` **auto-installs missing dependencies** for you — if `node_modules` or the
Python packages (flask, opencv, etc.) are absent, it automatically runs
`pip install -r backend/requirements.txt` and `npm install` before starting.
So a fresh clone only needs Python 3, Node.js ≥ 18, and this single command.
It starts both services together and stops them cleanly with Ctrl+C.

## Frontend (React)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api`, `/live_feed`, and `/static/uploads` to the
Flask backend on port 5000, so no CORS configuration is needed during development.

Production build:

```bash
cd frontend && npm run build   # outputs frontend/dist
```

## Backend (Flask)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                     # http://localhost:5000
```

Optionally set your own USDA API key via environment variable:

```bash
export USDA_API_KEY=your_key     # see backend/.env.example
```

If `frontend/dist` exists, Flask also serves the built React SPA at
http://localhost:5000 (client-side routes fall back to `index.html`).

## API Contract

| Endpoint | Method | Description |
|---|---|---|
| `/live_feed` | GET | MJPEG camera stream (consumed via `<img src="/live_feed">`) |
| `/api/capture` | POST | Captures current frame → YOLO prediction → USDA nutrition lookup → JSON `{prediction, image, calories, carbohydrates, protein, fat, fiber, sugar}` |
| `/capture`, `/result` | GET/POST | Legacy redirect-based Jinja flow (deprecated) |

## Routes

| Route | Description |
|---|---|
| React `/` | Home page – live camera feed + Capture button |
| React `/result` | Prediction + nutritional information card |
