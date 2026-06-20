import sqlite3
import hashlib
import json
from typing import Dict, Optional, Type
from pydantic import BaseModel

CACHE_DB_PATH = "summarize_prompts_cache.db"

def init_cache_db():
    """Initialize the SQLite cache database"""
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summarize_cache (
                prompt_hash TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,  -- store JSON as TEXT
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_cached_response(full_prompt: str) -> Optional[Dict]:
    """Retrieve cached response for a given prompt"""
    prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT response FROM summarize_cache WHERE prompt_hash = ?",
            (prompt_hash,)
        )
        result = cursor.fetchone()
    if result:
        return json.loads(result[0])
    return None

def cache_response(full_prompt: str, response: Type[BaseModel]):
    """Store a new prompt-response pair in the cache"""
    prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()
    response_json = response.model_dump_json()
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO summarize_cache (prompt_hash, prompt, response) VALUES (?, ?, ?)",
            (prompt_hash, full_prompt, response_json)
        )
        conn.commit()
