"""
src/api/main.py
Run:  uvicorn src.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from multiprocessing import Process

from src.api.routers import upload
from src.backend.flask_chat import app as flask_app

app = FastAPI(title="DEH Billing Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok"}


# Function to run the Flask app
def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)


# Start the Flask app in a separate process
flask_process = Process(target=run_flask)
flask_process.start()
