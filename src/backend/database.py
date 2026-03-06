import sqlite3
import os
import uuid
import json
from typing import List, Dict, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chat_history.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            image_urls TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    ''')
    
    # Run a safe migration if the column doesn't exist
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN image_urls TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_session(title: str = "New Chat") -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
        (session_id, title, datetime.utcnow())
    )
    conn.commit()
    conn.close()
    return session_id

def get_sessions() -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def save_message(session_id: str, role: str, content: str, image_urls: List[str] = None) -> str:
    msg_id = str(uuid.uuid4())
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (id, session_id, role, content, image_urls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, json.dumps(image_urls or []), datetime.utcnow())
    )
    # Autogenerate title if it's the first message and it's from the user
    if role == "user":
        c.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
        if c.fetchone()[0] == 1:
            title = content[:30] + "..." if len(content) > 30 else content
            c.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    
    conn.commit()
    conn.close()
    return msg_id

def rename_session(session_id: str, new_title: str) -> None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
    conn.commit()
    conn.close()

def delete_session(session_id: str) -> None:
    conn = get_connection()
    c = conn.cursor()
    # messages map to foreign key with ON DELETE CASCADE so they are destroyed automatically
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

# Initialize DB when the module is imported
init_db()
