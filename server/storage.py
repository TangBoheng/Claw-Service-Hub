"""SQLite-based data persistence layer.

Zero-dependency: uses Python's built-in sqlite3 module.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class Storage:
    """
    SQLite-based storage for service registry and related data.

    Thread-safe with write locking.
    """

    def __init__(self, db_path: str = "data/claw_service_hub.db"):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._write_lock = threading.Lock()

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._transaction() as conn:
            # Services table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT,
                    endpoint TEXT,
                    status TEXT DEFAULT 'online',
                    tags TEXT,
                    metadata TEXT,
                    emoji TEXT,
                    requires TEXT,
                    execution_mode TEXT,
                    interface_spec TEXT,
                    skill_doc TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # API keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_hash TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Request logs table (no FK constraint for flexibility)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    service_id TEXT,
                    method TEXT,
                    path TEXT,
                    status_code INTEGER,
                    duration_ms REAL,
                    error TEXT
                )
            """)

            # Ratings table (no FK constraint for flexibility)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT NOT NULL,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_status ON services(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_request_logs_timestamp ON request_logs(timestamp)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_service ON ratings(service_id)")

            # Key lifecycle table (for KeyManager persistence)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS key_lifecycle (
                    key TEXT PRIMARY KEY,
                    service_id TEXT NOT NULL,
                    consumer_id TEXT NOT NULL,
                    duration_seconds INTEGER DEFAULT 3600,
                    max_calls INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    call_count INTEGER DEFAULT 0
                )
            """)

            # Users table (for UserManager persistence)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")

    # ========== Service Operations ==========

    def save_service(self, service_data: Dict[str, Any]) -> None:
        """
        Save or update a service.

        Args:
            service_data: Service data dictionary
        """
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO services 
                    (id, name, description, version, endpoint, status, tags, 
                     metadata, emoji, requires, execution_mode, interface_spec, 
                     skill_doc, last_heartbeat)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        service_data.get("id"),
                        service_data.get("name"),
                        service_data.get("description"),
                        service_data.get("version"),
                        service_data.get("endpoint"),
                        service_data.get("status", "online"),
                        json.dumps(service_data.get("tags", [])),
                        json.dumps(service_data.get("metadata", {})),
                        service_data.get("emoji"),
                        json.dumps(service_data.get("requires", {})),
                        service_data.get("execution_mode"),
                        json.dumps(service_data.get("interface_spec", {})),
                        service_data.get("skill_doc"),
                        service_data.get("last_heartbeat", datetime.now()),
                    ),
                )

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get a service by ID."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()

        if row is None:
            return None
        return self._row_to_service_dict(row)

    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get all services."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM services ORDER BY last_heartbeat DESC").fetchall()
        return [self._row_to_service_dict(row) for row in rows]

    def delete_service(self, service_id: str) -> bool:
        """Delete a service by ID. Returns True if deleted."""
        with self._write_lock:
            with self._transaction() as conn:
                cursor = conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
                return cursor.rowcount > 0

    def find_services(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find services by criteria."""
        conn = self._get_connection()

        query = "SELECT * FROM services WHERE 1=1"
        params = []

        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")

        if status:
            query += " AND status = ?"
            params.append(status)

        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_service_dict(row) for row in rows]

    def _row_to_service_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to service dictionary."""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "version": row["version"],
            "endpoint": row["endpoint"],
            "status": row["status"],
            "tags": json.loads(row["tags"] or "[]"),
            "metadata": json.loads(row["metadata"] or "{}"),
            "emoji": row["emoji"],
            "requires": json.loads(row["requires"] or "{}"),
            "execution_mode": row["execution_mode"],
            "interface_spec": json.loads(row["interface_spec"] or "{}"),
            "skill_doc": row["skill_doc"],
            "first_seen": row["first_seen"],
            "last_heartbeat": row["last_heartbeat"],
        }

    # ========== API Key Operations ==========

    def save_api_key(self, key_hash: str, name: str, expires_at: Optional[datetime] = None) -> None:
        """Save an API key."""
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO api_keys (key_hash, name, expires_at)
                    VALUES (?, ?, ?)
                """,
                    (key_hash, name, expires_at),
                )

    def get_api_key(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key info."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1", (key_hash,)
        ).fetchone()

        if row is None:
            return None

        # Check expiration
        expires_at = row["expires_at"]
        if expires_at:
            # Handle both string and datetime types
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at < datetime.now():
                return None

        return dict(row)

    def update_key_usage(self, key_hash: str) -> None:
        """Update last_used timestamp for an API key."""
        with self._transaction() as conn:
            conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE key_hash = ?", (datetime.now(), key_hash)
            )

    def deactivate_api_key(self, key_hash: str) -> bool:
        """Deactivate an API key."""
        with self._write_lock:
            with self._transaction() as conn:
                cursor = conn.execute(
                    "UPDATE api_keys SET is_active = 0 WHERE key_hash = ?", (key_hash,)
                )
                return cursor.rowcount > 0

    # ========== Request Log Operations ==========

    def log_request(
        self,
        service_id: Optional[str],
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log a request."""
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO request_logs 
                    (service_id, method, path, status_code, duration_ms, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (service_id, method, path, status_code, duration_ms, error),
                )

    def get_request_logs(
        self, service_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get request logs."""
        conn = self._get_connection()

        query = "SELECT * FROM request_logs"
        params = []

        if service_id:
            query += " WHERE service_id = ?"
            params.append(service_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    # ========== Rating Operations ==========

    def save_rating(self, service_id: str, rating: int, comment: Optional[str] = None) -> None:
        """Save a service rating."""
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO ratings (service_id, rating, comment)
                    VALUES (?, ?, ?)
                """,
                    (service_id, rating, comment),
                )

    def get_service_ratings(self, service_id: str) -> List[Dict[str, Any]]:
        """Get all ratings for a service."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM ratings WHERE service_id = ? ORDER BY created_at DESC", (service_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_service_average_rating(self, service_id: str) -> Optional[float]:
        """Get average rating for a service."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT AVG(rating) as avg FROM ratings WHERE service_id = ?", (service_id,)
        ).fetchone()
        return row["avg"] if row and row["avg"] is not None else None

    # ========== Key Lifecycle Operations ==========

    def save_key(self, key_data: Dict[str, Any]) -> None:
        """
        Save or update a key lifecycle.

        Args:
            key_data: Key data dictionary with: key, service_id, consumer_id,
                     duration_seconds, max_calls, created_at, is_active, call_count
        """
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO key_lifecycle 
                    (key, service_id, consumer_id, duration_seconds, max_calls, 
                     created_at, expires_at, is_active, call_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        key_data.get("key"),
                        key_data.get("service_id"),
                        key_data.get("consumer_id"),
                        key_data.get("duration_seconds", 3600),
                        key_data.get("max_calls", 100),
                        key_data.get("created_at"),
                        key_data.get("expires_at"),
                        1 if key_data.get("is_active", True) else 0,
                        key_data.get("call_count", 0),
                    ),
                )

    def get_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Get key lifecycle by key string."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM key_lifecycle WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def get_all_keys(self) -> List[Dict[str, Any]]:
        """Get all key lifecycles."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM key_lifecycle").fetchall()
        return [dict(row) for row in rows]

    def update_key_usage(self, key: str, increment: bool = True) -> bool:
        """Update key usage count."""
        with self._write_lock:
            with self._transaction() as conn:
                cursor = conn.cursor()
                if increment:
                    cursor.execute(
                        "UPDATE key_lifecycle SET call_count = call_count + 1 WHERE key = ?", (key,)
                    )
                return cursor.rowcount > 0

    def deactivate_key(self, key: str) -> bool:
        """Deactivate a key."""
        with self._write_lock:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE key_lifecycle SET is_active = 0 WHERE key = ?", (key,))
                return cursor.rowcount > 0

    # ========== User Operations ==========

    def save_user(self, user_data: Dict[str, Any]) -> None:
        """
        Save or update a user.

        Args:
            user_data: User data dictionary with: user_id, name, api_key, created_at, is_active
        """
        with self._write_lock:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO users 
                    (user_id, name, api_key, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        user_data.get("user_id"),
                        user_data.get("name"),
                        user_data.get("api_key"),
                        user_data.get("created_at"),
                        1 if user_data.get("is_active", True) else 0,
                    ),
                )

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by user_id."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user by API key."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(row) for row in rows]

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        with self._write_lock:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                return cursor.rowcount > 0

    # ========== Utility Methods ==========

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def vacuum(self) -> None:
        """Optimize database."""
        with self._transaction() as conn:
            conn.execute("VACUUM")


# Global storage instance
_storage: Optional[Storage] = None


def get_storage(db_path: str = "data/claw_service_hub.db") -> Storage:
    """
    Get or create global storage instance.

    Args:
        db_path: Path to SQLite database

    Returns:
        Storage instance
    """
    global _storage
    if _storage is None:
        _storage = Storage(db_path)
    return _storage


def init_storage(db_path: str = "data/claw_service_hub.db") -> Storage:
    """
    Initialize storage with specific path (useful for testing).

    Args:
        db_path: Path to SQLite database

    Returns:
        Storage instance
    """
    global _storage
    if _storage:
        _storage.close()
    _storage = Storage(db_path)
    return _storage
