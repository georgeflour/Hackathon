"""
src/api/main.py
Run:  uvicorn src.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import upload

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
