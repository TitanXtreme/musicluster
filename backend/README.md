# Spotify Cluster Predictor

## Backend API

From the repository root, install the Python dependencies and start the API:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn main:app --app-dir backend/api --reload
```

The API runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health`
to verify it has loaded the model and dataset.

## React frontend

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal. The frontend sends API requests to
`http://localhost:8000`.

## Project folders

- `backend/api/` — FastAPI application
- `frontend/` — React application and Vite configuration
- `backend/data/` — Spotify track datasets
- `backend/models/` — trained model and parameters
- `backend/notebooks/` — analysis and feature-engineering notebooks
- `backend/scripts/` — model training, tuning, and prediction tools
