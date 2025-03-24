from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
import os
import logging
from contextlib import contextmanager

from peewee import (
    Model, SqliteDatabase, CharField, DateTimeField, ForeignKeyField,
    TextField, AutoField, BooleanField, DoesNotExist
)

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
THIS_DIR = Path(__file__).parent.parent
DB_DIR = THIS_DIR / 'db'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "sessions.db"

# Singleton database instance
DB_INSTANCE = None


def get_db():
    """Get the database connection"""
    global DB_INSTANCE
    if DB_INSTANCE is None:
        db_path = DB_PATH.resolve()
        DB_INSTANCE = SqliteDatabase(
            db_path,
            pragmas={
                'journal_mode': 'wal',
                'foreign_keys': 1,
                'synchronous': 0
            }
        )
    return DB_INSTANCE


class BaseModel(Model):
    """Base model with database connection"""
    class Meta:
        database = get_db()


class Session(BaseModel):
    """Model for tracking sessions"""
    id = CharField(primary_key=True)
    user_id = CharField(null=True)
    client_id = CharField(null=True)
    form_class = CharField(null=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    last_active = DateTimeField(default=datetime.now)


class SessionState(BaseModel):
    """Model for tracking form states within a session"""
    id = AutoField()
    session = ForeignKeyField(Session, backref='states')
    state_data = TextField()
    progress = TextField(null=True)
    timestamp = DateTimeField(default=datetime.now)


class SessionDBManager:
    """Manager for session and state persistence using Peewee ORM with caching"""

    def __init__(self, session_id: str = None, verbose: bool = False):
        """Initialize the session database manager.

        Args:
            session_id: Optional session identifier
            verbose: Whether to show detailed log messages
        """
        self.db = get_db()
        if self.db.is_closed():
            self.db.connect()

        self.verbose = verbose
        self.session_id = session_id
        self._session = None
        self._cache = {}  # {session_id: (timestamp, state_data)}
        self._cache_timeout = 30

        # Set log level based on verbose setting
        logger.setLevel(logging.INFO if verbose else logging.WARNING)

        # Create tables if they don't exist
        self.db.create_tables([Session, SessionState], safe=True)

        self._log(f"SessionDBManager initialized with session_id: {session_id}")

    def _log(self, message: str, level: str = "info"):
        """Log a message with the appropriate level"""
        if not self.verbose and level not in ["error", "warning"]:
            return
        getattr(logger, level)(message)

    @contextmanager
    def session_context(self, session_id: str = None):
        """Context manager for session operations"""
        old_session = self._session
        try:
            if session_id:
                self._session = self.get_or_create_session(session_id)
            yield self
        finally:
            self._session = old_session

    @contextmanager
    def temporary_session(self, session_id: str):
        """Context manager for temporarily switching to another session

        Args:
            session_id: The session ID to temporarily switch to
        """
        old_session_id = self.session_id
        old_session = self._session

        try:
            self.session_id = session_id
            self._session = None
            yield self
        finally:
            self.session_id = old_session_id
            self._session = old_session

    def get_or_create_session(
        self,
        session_id: str = None,
        user_id: str = None,
        client_id: str = None,
        form_class: str = None
    ) -> Session:
        """Get existing session or create new one"""
        if session_id:
            try:
                session = Session.get(Session.id == session_id)
                self._log(f"Retrieved existing session: {session_id}")
                return session
            except DoesNotExist:
                self._log(f"Session not found: {session_id}", "warning")

        # Create new session
        new_id = str(uuid.uuid4())
        session = Session.create(
            id=new_id,
            user_id=user_id,
            client_id=client_id,
            form_class=form_class,
            active=True,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        self._log(f"Created new session: {new_id}")
        return session

    def update_session_activity(self) -> bool:
        """Update the last_active timestamp for the current session"""
        if not self._session:
            return False

        try:
            self._session.last_active = datetime.now()
            self._session.save()
            return True
        except Exception as e:
            self._log(f"Error updating session activity: {e}", "error")
            return False

    def save_state(
        self,
        state_data: Union[Dict[str, Any], str],
        progress: int = None,
        user_id: str = None,
        client_id: str = None,
        form_class: str = None
    ) -> bool:
        """Save a state to the database"""
        session = self.get_or_create_session(
            self.session_id,
            user_id=user_id,
            client_id=client_id,
            form_class=form_class
        )
        if not session:
            return False

        # Convert dict to JSON if necessary
        state_json = json.dumps(state_data) if isinstance(state_data, dict) else state_data

        # Update session activity
        self.update_session_activity()

        try:
            timestamp = datetime.now()
            SessionState.create(
                session=session,
                state_data=state_json,
                progress=progress,
                timestamp=timestamp
            )

            # Update cache
            self._cache[session.id] = (timestamp, json.loads(state_json))
            self._log(f"Saved state to session {session.id}")
            return True
        except Exception as e:
            self._log(f"Error saving state: {e}", "error")
            return False

    def get_latest_state(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get the latest state for the current session"""
        if not self._session:
            return None

        # Check cache first if enabled
        if use_cache and self._session.id in self._cache:
            timestamp, state_data = self._cache[self._session.id]
            if (datetime.now() - timestamp).total_seconds() < self._cache_timeout:
                return state_data

        try:
            latest_state = (
                SessionState.select()
                .where(SessionState.session == self._session)
                .order_by(SessionState.timestamp.desc())
                .first()
            )

            if latest_state:
                state_data = json.loads(latest_state.state_data)
                self._cache[self._session.id] = (latest_state.timestamp, state_data)
                return state_data
        except Exception as e:
            self._log(f"Error getting latest state: {e}", "error")

        return None

    def get_state_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all historical states for a session"""
        if not self._session:
            return []

        try:
            query = (
                SessionState.select()
                .where(SessionState.session == self._session)
                .order_by(SessionState.timestamp.asc())
            )

            if limit is not None:
                query = query.limit(limit)

            result = []
            for state in query:
                try:
                    state_data = json.loads(state.state_data)
                    state_data['timestamp'] = state.timestamp.isoformat()
                    state_data['progress'] = state.progress
                    result.append(state_data)
                except json.JSONDecodeError:
                    self._log("Invalid JSON in state data", "warning")
                    continue

            return result
        except Exception as e:
            self._log(f"Error getting state history: {e}", "error")
            return []

    def clear_cache(self, session_id: str = None):
        """Clear state cache for a session or all sessions"""
        if session_id:
            if session_id in self._cache:
                del self._cache[session_id]
                self._log(f"Cleared cache for session {session_id}")
        else:
            self._cache.clear()
            self._log("Cleared all cached states")

    def close_session(self):
        """Close the current session"""
        if self._session:
            self._session.active = False
            self._session.save()
            self._log(f"Closed session {self._session.id}")

    def delete_session(self):
        """Delete the current session and all associated states"""
        if self._session:
            # Delete states first (foreign key constraint)
            SessionState.delete().where(SessionState.session == self._session).execute()
            # Then delete session
            self._session.delete_instance()
            self._session = None
            self.session_id = None
            self._log(f"Deleted session and associated states")

    def check_database(self) -> bool:
        """Check if the database is accessible and properly configured"""
        try:
            db_path = Path(self.db.database)
            exists = db_path.exists()
            self._log(f"Database file exists: {exists} at {db_path}")

            if exists:
                writable = os.access(db_path, os.W_OK)
                self._log(f"Database file is writable: {writable}")

                if Session.table_exists() and SessionState.table_exists():
                    self._log("Database tables exist")
                    return True
            else:
                # Create database and tables
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.db.close()
                self.db.connect()
                self.db.create_tables([Session, SessionState], safe=True)
                self._log("Created database and tables")
                return True

        except Exception as e:
            self._log(f"Database check error: {e}", "error")
            return False

    def set_verbose(self, verbose: bool):
        """Set verbosity level"""
        self.verbose = verbose
        logger.setLevel(logging.INFO if verbose else logging.WARNING)
