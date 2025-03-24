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
        self._session = None
        self._cache = {}  # {session_id: (timestamp, state_data)}
        self._cache_timeout = 30

        # Set log level based on verbose setting
        logger.setLevel(logging.INFO if verbose else logging.WARNING)

        # Create tables if they don't exist
        self.db.create_tables([Session, SessionState], safe=True)

        # Initialize session if provided
        if session_id:
            self.set_session(session_id)

    @property
    def session_id(self) -> str:
        """Get current session ID"""
        return self._session.id if self._session else None

    def set_session(self, session_id: str) -> bool:
        """Set the active session

        Args:
            session_id: Session ID to set

        Returns:
            bool: True if session was set successfully
        """
        try:
            self._session = Session.get(Session.id == session_id)
            self._log(f"Set active session: {session_id}")
            return True
        except DoesNotExist:
            self._log(f"Session not found: {session_id}", "warning")
            return False

    def create_session(
        self,
        user_id: str = None,
        client_id: str = None,
        form_class: str = None
    ) -> Session:
        """Create a new session

        Args:
            user_id: Optional user ID
            client_id: Optional client ID
            form_class: Optional form class name

        Returns:
            Created session
        """
        session = Session.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            client_id=client_id,
            form_class=form_class,
            active=True,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        self._session = session
        self._log(f"Created new session: {session.id}")
        return session

    def get_or_create_session(
        self,
        session_id: str = None,
        user_id: str = None,
        client_id: str = None,
        form_class: str = None
    ) -> Session:
        """Get existing session or create new one"""
        # If session_id is provided, try to get that specific session
        if session_id:
            try:
                self._session = Session.get(Session.id == session_id)
                self._log(f"Using existing session: {session_id}")
                return self._session
            except DoesNotExist:
                self._log(f"Session {session_id} not found")
                return None

        # Only create a new session if no session_id was provided
        if not self._session:
            session = self.create_session(user_id, client_id, form_class)
            self._log(f"Created new session: {session.id}")
            return session

        self._log(f"Using current session: {self._session.id}")
        return self._session

    def save_state(self, state_data: dict) -> bool:
        """Save current state to database

        Args:
            state_data: State data to save

        Returns:
            bool: True if state was saved successfully
        """
        if not self._session:
            self._log("No active session to save state to", "warning")
            return False

        try:
            # Convert state data to JSON if it's a dict
            if isinstance(state_data, dict):
                state_data = json.dumps(state_data)

            # Create new state record
            state = SessionState.create(
                session=self._session,
                state_data=state_data,
                timestamp=datetime.now()
            )

            # Update session activity
            self._session.last_active = datetime.now()
            self._session.save()

            # Update cache
            self._cache[self._session.id] = (state.timestamp, json.loads(state_data))

            self._log(f"Saved state {state.id} for session {self._session.id}")
            self._log(f"State data: {state_data}")
            return True
        except Exception as e:
            self._log(f"Error saving state: {e}", "error")
            return False

    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """Get the latest state for the current session"""
        if not self._session:
            return None

        # Check cache first
        if self._session.id in self._cache:
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

    def get_state_history(self, session_id: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get history of states for current session

        Args:
            session_id: Optional session ID to get history for
            limit: Optional limit on number of states to return

        Returns:
            List of state dictionaries
        """
        if session_id:
            self.set_session(session_id)

        if not self._session:
            self._log("No active session to get state history from", "warning")
            return []

        try:
            query = SessionState.select().where(
                SessionState.session == self._session
            ).order_by(SessionState.timestamp)

            if limit:
                query = query.limit(limit)

            states = []
            for state in query:
                state_data = json.loads(state.state_data)
                states.append({
                    'session_id': self._session.id,
                    'timestamp': state.timestamp,
                    'state': state_data
                })

            self._log(f"Retrieved {len(states)} states for session {self._session.id}")
            return states
        except Exception as e:
            self._log(f"Error getting state history: {e}", "error")
            return []

    def clear_cache(self):
        """Clear state cache"""
        self._cache.clear()
        self._log("Cleared state cache")

    def close_session(self):
        """Close the current session"""
        if self._session:
            self._session.active = False
            self._session.save()
            self._log(f"Closed session {self._session.id}")
            self._session = None

    def delete_session(self):
        """Delete the current session and all associated states"""
        if self._session:
            # Delete states first
            SessionState.delete().where(SessionState.session == self._session).execute()
            # Then delete session
            self._session.delete_instance()
            self._session = None
            self._log("Deleted session and associated states")

    def _log(self, message: str, level: str = "info"):
        """Log a message with the appropriate level"""
        if not self.verbose and level not in ["error", "warning"]:
            return
        getattr(logger, level)(message)

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
