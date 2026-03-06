from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from src.backend import database

router = APIRouter(prefix="/history", tags=["history"])

class CreateSessionRequest(BaseModel):
    title: str = "New Chat"

class RenameSessionRequest(BaseModel):
    title: str

class SaveMessageRequest(BaseModel):
    role: str
    content: str
    image_urls: List[str] = []

@router.get("/sessions")
def get_sessions():
    """Returns all chat sessions, most recent first."""
    sessions = database.get_sessions()
    return {"sessions": sessions}

@router.post("/sessions")
def create_session(req: CreateSessionRequest):
    """Creates a new chat session."""
    session_id = database.create_session(req.title)
    return {"session_id": session_id}

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    """Returns all messages for a given session ID."""
    messages = database.get_messages(session_id)
    return {"messages": messages}

@router.post("/sessions/{session_id}/messages")
def save_message(session_id: str, req: SaveMessageRequest):
    """Appends a new message to the given session."""
    msg_id = database.save_message(session_id, req.role, req.content, req.image_urls)
    return {"message_id": msg_id, "status": "success"}

@router.put("/sessions/{session_id}")
def rename_session(session_id: str, req: RenameSessionRequest):
    """Renames an existing session."""
    database.rename_session(session_id, req.title)
    return {"status": "success"}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Deletes an entire session and automagically cascade-deletes messages."""
    database.delete_session(session_id)
    return {"status": "success"}
