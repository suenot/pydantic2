from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Union, List, Tuple
import os
import time
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

# Singleton database instance and connection pool
DB_INSTANCE = None
_STATE_CACHE = {}  # Cache for states: {session_id: (timestamp, state_data)}
_CACHE_TIMEOUT = 30  # Cache timeout in seconds


def get_db():
    """Get the database connection"""
    global DB_INSTANCE
    if DB_INSTANCE is None:
        db_path = DB_PATH.resolve()
        DB_INSTANCE = SqliteDatabase(
            db_path,
            pragmas={
                'journal_mode': 'wal',      # Write-ahead logging for better concurrency
                'foreign_keys': 1,          # Enforce foreign key constraints
                'synchronous': 0            # Reduce fsync calls for better performance
            }
        )
    return DB_INSTANCE


class BaseModel(Model):
    """Base model with database connection"""
    class Meta:
        database = get_db()


class Session(BaseModel):
    """Model for tracking sessions"""
    id = CharField(primary_key=True)  # UUID as primary key
    user_id = CharField(null=True)
    client_id = CharField(null=True)
    form_class = CharField(null=True)  # Name of the form class used
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    last_active = DateTimeField(default=datetime.now)


class SessionState(BaseModel):
    """Model for tracking form states within a session"""
    id = AutoField()
    session = ForeignKeyField(Session, backref='states')
    state_data = TextField()  # JSON serialized state
    progress = TextField(null=True)  # Progress percentage 0-100
    timestamp = DateTimeField(default=datetime.now)


class SessionDBManager:
    """Manager for session and state persistence using Peewee ORM with caching"""

    def __init__(self, session_id: str = None, verbose: bool = False):
        """Initialize the session database manager.

        Args:
            session_id: Optional session identifier. If None, a new session will be
                created when needed.
            verbose: Whether to show detailed log messages
        """
        self.db = get_db()
        if self.db.is_closed():
            self.db.connect()

        self.verbose = verbose
        self.session_id = session_id
        self._session = None
        self._last_state_fetch_time = 0
        self._last_state = None

        # Set log level based on verbose setting
        if self.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        # Create tables if they don't exist
        self.db.create_tables([Session, SessionState], safe=True)

        self._log(f"SessionDBManager initialized with session_id: {session_id}")

    def _log(self, message: str, level: str = "info", *args, **kwargs):
        """Log a message with the appropriate level

        Args:
            message: The message to log
            level: The log level (info, warning, error, debug)
        """
        if not self.verbose and level not in ["error", "warning"]:
            return

        log_func = getattr(logger, level)
        log_func(message, *args, **kwargs)

    @contextmanager
    def _operation(self):
        """Context manager for database operations with automatic reconnection"""
        try:
            if self.db.is_closed():
                self.db.connect()
            yield
        except Exception as e:
            self._log(f"Database operation error: {e}", "error")
            raise

    def _create_session(
        self, user_id: str = None, client_id: str = None, form_class: str = None
    ) -> Session:
        """Create a new session"""
        try:
            with self._operation():
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
                self.session_id = new_id
                self._session = session
                self._log(f"Created new session: {new_id}")
                return session
        except Exception as e:
            self._log(f"Error creating session: {e}", "error")
            raise

    def ensure_session(
        self, user_id: str = None, client_id: str = None, form_class: str = None
    ) -> Session:
        """Ensure a session exists, creating one if needed

        Args:
            user_id: Optional user identifier
            client_id: Optional client identifier
            form_class: Optional form class name

        Returns:
            Session object
        """
        # Get existing session if available
        session = self.get_session(create_if_missing=False)
        if session:
            self._log(f"Using existing session: {session.id}")
            return session

        # Create new session if none exists
        return self._create_session(user_id, client_id, form_class)

    def get_session(
        self,
        create_if_missing: bool = True,
        user_id: str = None,
        client_id: str = None,
        form_class: str = None
    ) -> Optional[Session]:
        """Get the current session, optionally creating if it doesn't exist"""
        # Return cached session if available
        if self._session is not None:
            return self._session

        # Try to get existing session
        if self.session_id:
            try:
                with self._operation():
                    session = Session.get(Session.id == self.session_id)
                    self._session = session
                    self._log(f"Retrieved session: {session.id}")
                    return session
            except DoesNotExist:
                self._log(f"Session not found with ID: {self.session_id}", "warning")
                pass  # Session not found, will create if requested
            except Exception as e:
                self._log(f"Error getting session: {e}", "error")
                # Continue to create if requested

        # Create new session if requested and needed
        if create_if_missing:
            return self._create_session(user_id, client_id, form_class)

        return None

    def update_session_activity(self) -> bool:
        """Update the last_active timestamp for the current session"""
        session = self.get_session(create_if_missing=False)
        if not session:
            self._log("No session to update activity", "warning")
            return False

        try:
            with self._operation():
                session.last_active = datetime.now()
                session.save()
                return True
        except Exception as e:
            self._log(f"Error updating session activity: {e}", "error")
            return False

    def save_state(
        self, state_data: Union[Dict[str, Any], str], progress: int = None,
        user_id: str = None, client_id: str = None, form_class: str = None
    ) -> bool:
        """Save a state to the database

        Args:
            state_data: State data as dictionary or JSON string
            progress: Optional progress percentage (0-100)
            user_id: Optional user ID to create session if needed
            client_id: Optional client ID to create session if needed
            form_class: Optional form class name to create session if needed

        Returns:
            True if saved successfully, False otherwise
        """
        session = self.get_session(
            create_if_missing=True,
            user_id=user_id,
            client_id=client_id,
            form_class=form_class
        )
        if not session:
            self._log("Failed to get or create session for saving state", "error")
            return False

        # Convert dict to JSON if necessary
        if isinstance(state_data, dict):
            state_json = json.dumps(state_data)
        else:
            state_json = state_data

        # Update session activity
        self.update_session_activity()

        # Create state record
        try:
            with self._operation():
                timestamp = datetime.now()
                state_record = SessionState.create(
                    session=session,
                    state_data=state_json,
                    progress=progress,
                    timestamp=timestamp
                )

                # Update cache
                session_id = session.id
                _STATE_CACHE[session_id] = (timestamp, json.loads(state_json))
                self._last_state = json.loads(state_json)
                self._last_state_fetch_time = time.time()

                self._log(f"Saved state to session {session.id} with progress {progress}")
                return True
        except Exception as e:
            self._log(f"Error saving state: {e}", "error")
            return False

    def get_latest_state(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get the latest state for the current session

        Args:
            use_cache: Whether to use cached state if available and fresh

        Returns:
            Dictionary with state data or None if no state exists
        """
        session = self.get_session(create_if_missing=False)
        if not session:
            return None

        session_id = session.id

        # Check cache first if enabled
        if use_cache:
            # If we have a recently cached state, use it
            if self._last_state and time.time() - self._last_state_fetch_time < _CACHE_TIMEOUT:
                self._log("Using locally cached state", "debug")
                return self._last_state

            # Check global cache
            if session_id in _STATE_CACHE:
                timestamp, state_data = _STATE_CACHE[session_id]
                # Check if cache is still valid
                seconds_since_update = (datetime.now() - timestamp).total_seconds()
                if seconds_since_update < _CACHE_TIMEOUT:
                    self._log("Using globally cached state", "debug")
                    self._last_state = state_data
                    self._last_state_fetch_time = time.time()
                    return state_data

        # Cache miss or disabled, fetch from database
        try:
            with self._operation():
                # First check if the session has any states before querying
                states_exist = (
                    SessionState.select()
                    .where(SessionState.session == session)
                    .exists()
                )

                if not states_exist:
                    self._log(f"No states found for session {session_id}", "debug")
                    return None

                latest_state = (
                    SessionState.select()
                    .where(SessionState.session == session)
                    .order_by(SessionState.timestamp.desc())
                    .get()
                )

                # Update cache
                state_data = json.loads(latest_state.state_data)
                _STATE_CACHE[session_id] = (latest_state.timestamp, state_data)
                self._last_state = state_data
                self._last_state_fetch_time = time.time()

                self._log("Retrieved latest state from database", "debug")
                return state_data
        except json.JSONDecodeError as e:
            self._log(f"Error decoding state data: {e}", "error")
            return None
        except Exception as e:
            self._log(f"Error getting latest state: {e}", "debug")
            return None

    def get_state_history(self, session_id: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get all historical states for a session in chronological order with efficient querying

        Args:
            session_id: Optional session ID. If None, uses current session
            limit: Optional limit on the number of states to return

        Returns:
            List of state dictionaries ordered by timestamp (oldest first)
        """
        # Use provided session_id or current session
        current_session_id = self.session_id
        if session_id:
            self.session_id = session_id

        session = self.get_session(create_if_missing=False)
        if not session:
            # Restore original session_id
            if session_id:
                self.session_id = current_session_id
            return []

        try:
            with self._operation():
                # Build query with optimizations
                query = (
                    SessionState.select()
                    .where(SessionState.session == session)
                    .order_by(SessionState.timestamp.asc())
                )

                # Apply limit if specified
                if limit:
                    query = query.limit(limit)

                # Batch process results to reduce memory usage
                result = []
                batch_size = 50  # Process in batches to avoid large memory usage
                count = query.count()
                self._log(f"Found {count} states in session {session.id}", "debug")

                for i in range(0, count, batch_size):
                    batch = query.offset(i).limit(batch_size)

                    for state in batch:
                        try:
                            state_data = json.loads(state.state_data)
                            # Add timestamp for reference
                            state_data['timestamp'] = state.timestamp.isoformat()
                            state_data['progress'] = state.progress
                            result.append(state_data)
                        except json.JSONDecodeError:
                            self._log("Invalid JSON in state data", "warning")
                            continue

                # Restore original session_id
                if session_id:
                    self.session_id = current_session_id

                return result
        except Exception as e:
            self._log(f"Error getting state history: {e}", "error")
            # Restore original session_id
            if session_id:
                self.session_id = current_session_id
            return []

    @contextmanager
    def temporary_session(self, session_id: str):
        """Context manager for temporarily switching to another session

        Args:
            session_id: The session ID to temporarily switch to
        """
        original_id = self.session_id
        original_session = self._session

        try:
            self.session_id = session_id
            self._session = None
            self._log(f"Temporarily switched to session: {session_id}", "debug")
            yield self
        finally:
            self.session_id = original_id
            self._session = original_session
            self._log("Restored original session", "debug")

    def set_verbose(self, verbose: bool):
        """Set verbosity level

        Args:
            verbose: Whether to display detailed logs
        """
        self.verbose = verbose
        if self.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

    def clear_cache(self, session_id: str = None):
        """Clear state cache for a session or all sessions

        Args:
            session_id: Optional session ID. If None, clears all cached states
        """
        if session_id:
            if session_id in _STATE_CACHE:
                del _STATE_CACHE[session_id]
                self._log(f"Cleared cache for session {session_id}", "debug")
            if self.session_id == session_id:
                self._last_state = None
                self._last_state_fetch_time = 0
        else:
            _STATE_CACHE.clear()
            self._last_state = None
            self._last_state_fetch_time = 0
            self._log("Cleared all cached states", "debug")

    def close_session(self):
        """Close the current session"""
        session = self.get_session(create_if_missing=False)
        if session:
            with self._operation():
                session.active = False
                session.save()
                self._log(f"Closed session {session.id}")

    def delete_session(self):
        """Delete the current session and all associated states"""
        session = self.get_session(create_if_missing=False)
        if session:
            with self._operation():
                # First delete states (foreign key constraint)
                state_count = SessionState.delete().where(SessionState.session == session).execute()
                # Then delete session
                session.delete_instance()
                self._session = None
                self.session_id = None
                self._log(f"Deleted session {session.id} with {state_count} states")

    def check_database(self) -> bool:
        """Check if the database file exists and is writable

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            # Get the database file path
            db_path = Path(self.db.database)

            # Check if the file exists
            exists = db_path.exists()
            self._log(f"Database file exists: {exists} at {db_path}")

            if exists:
                # Check if it's writable
                writable = os.access(db_path, os.W_OK)
                self._log(f"Database file is writable: {writable}")

                # Verify table structure
                if Session.table_exists():
                    self._log("Session table exists")
                if SessionState.table_exists():
                    self._log("SessionState table exists")

                # Try a test query
                session_count = Session.select().count()
                self._log(f"Found {session_count} sessions in database")

                return True
            else:
                # Try to create the parent directory if it doesn't exist
                parent_dir = db_path.parent
                if not parent_dir.exists():
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    self._log(f"Created parent directory: {parent_dir}")

                # Try to create and write to the database
                with open(db_path, 'w') as f:
                    f.write('')
                self._log(f"Created empty database file at {db_path}")

                # Reconnect database and create tables
                self.db.close()
                self.db.connect()
                self.db.create_tables([Session, SessionState], safe=True)
                self._log("Created database tables")

                return True
        except Exception as e:
            self._log(f"Database check error: {e}", "error")
            return False

    def debug_session_info(self, session_id: str = None):
        """Print debug information about a session

        Args:
            session_id: Optional session ID to debug, uses current if None
        """
        target_id = session_id or self.session_id
        if not target_id:
            self._log("No session_id to debug", "warning")
            return

        self._log(f"\n=== Session Debug Info for {target_id} ===")

        # Check if session exists
        try:
            session = Session.get(Session.id == target_id)
            self._log(f"Session found: {session.id}")
            self._log(f"  User ID: {session.user_id}")
            self._log(f"  Client ID: {session.client_id}")
            self._log(f"  Form Class: {session.form_class}")
            self._log(f"  Created: {session.created_at}")
            self._log(f"  Last Active: {session.last_active}")
            self._log(f"  Active: {session.active}")

            # Count states
            states = SessionState.select().where(SessionState.session == session)
            state_count = states.count()
            self._log(f"Session has {state_count} states")

            if state_count > 0:
                # Show latest state
                latest = states.order_by(SessionState.timestamp.desc()).first()
                self._log(f"Latest state: {latest.timestamp}")
                self._log(f"Latest progress: {latest.progress}%")
        except DoesNotExist:
            self._log(f"Session not found with ID: {target_id}", "warning")
        except Exception as e:
            self._log(f"Error getting session debug info: {e}", "error")

        self._log("=== End Debug Info ===\n")
