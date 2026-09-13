"""Database management and SQLite schema repository."""
import os
import sqlite3
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    """SQLite Database manager for persistent storage."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DB_PATH
        self._init_tables()

    @contextmanager
    def get_connection(self):
        """Context manager for SQLite database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tables(self):
        """Initialize all required SQLite schema tables if they do not exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS practice_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS speech_attempts (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            user_id TEXT,
            target_text TEXT NOT NULL,
            original_transcript TEXT NOT NULL,
            corrected_transcript TEXT NOT NULL,
            duration_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS corrections (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            incorrect_text TEXT NOT NULL,
            correct_text TEXT NOT NULL,
            context_phrase TEXT,
            occurrence_count INTEGER DEFAULT 1,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pronunciation_results (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL,
            overall_score REAL NOT NULL,
            confidence REAL NOT NULL,
            words_json TEXT,
            issues_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (attempt_id) REFERENCES speech_attempts(id)
        );

        CREATE TABLE IF NOT EXISTS accent_results (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL,
            accent_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            model_status TEXT NOT NULL,
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (attempt_id) REFERENCES speech_attempts(id)
        );

        CREATE TABLE IF NOT EXISTS feedback_records (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL,
            summary TEXT,
            pronunciation_feedback TEXT,
            accent_feedback TEXT,
            strengths_json TEXT,
            areas_json TEXT,
            exercises_json TEXT,
            provider TEXT,
            is_fallback INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (attempt_id) REFERENCES speech_attempts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_corrections_user ON corrections(user_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_user ON speech_attempts(user_id);
        """
        with self.get_connection() as conn:
            conn.executescript(schema)
        logger.info(f"Database initialized at '{self.db_path}'.")


# Global database instance
db = Database()
