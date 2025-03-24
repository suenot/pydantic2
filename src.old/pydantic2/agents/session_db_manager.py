from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
import os

from peewee import (
    Model, SqliteDatabase, CharField, DateTimeField, ForeignKeyField,
    TextField, AutoField, BooleanField, DoesNotExist
)

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
        # Print path for debugging
        print(f"Database path: {db_path}")
        DB_INSTANCE = SqliteDatabase(db_path)
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
    """Manager for session and state persistence using Peewee ORM"""

    def __init__(self, session_id: str = None):
        """Initialize the session database manager.

        Args:
            session_id: Optional session identifier. If None, a new session will be
                created when needed.
        """
        self.db = get_db()
        if self.db.is_closed():
            self.db.connect()

        # Create tables if they don't exist
        self.db.create_tables([Session, SessionState], safe=True)

        self.session_id = session_id
        self._session = None
        print(f"SessionDBManager initialized with session_id: {session_id}")

    def _create_session(
        self, user_id: str = None, client_id: str = None, form_class: str = None
    ) -> Session:
        """Create a new session"""
        try:
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
            print(f"Created new session: {new_id}")
            return session
        except Exception as e:
            print(f"Error creating session: {e}")
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
            print(f"Using existing session: {session.id}")
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
                session = Session.get(Session.id == self.session_id)
                self._session = session
                print(f"Retrieved session: {session.id}")
                return session
            except DoesNotExist:
                print(f"Session not found with ID: {self.session_id}")
                pass  # Session not found, will create if requested
            except Exception as e:
                print(f"Error getting session: {e}")
                # Continue to create if requested

        # Create new session if requested and needed
        if create_if_missing:
            return self._create_session(user_id, client_id, form_class)

        return None

    def update_session_activity(self) -> bool:
        """Update the last_active timestamp for the current session"""
        session = self.get_session(create_if_missing=False)
        if not session:
            print("No session to update activity")
            return False

        try:
            session.last_active = datetime.now()
            session.save()
            return True
        except Exception as e:
            print(f"Error updating session activity: {e}")
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
            print("Failed to get or create session for saving state")
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
            state = SessionState.create(
                session=session,
                state_data=state_json,
                progress=progress,
                timestamp=datetime.now()
            )
            print(f"Saved state to session {session.id} with progress {progress}")
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """Get the latest state for the current session

        Returns:
            Dictionary with state data or None if no state exists
        """
        session = self.get_session(create_if_missing=False)
        if not session:
            return None

        try:
            # Get the latest state for this session
            latest_state = (
                SessionState.select()
                .where(SessionState.session == session)
                .order_by(SessionState.timestamp.desc())
                .get()
            )
            return json.loads(latest_state.state_data)
        except (DoesNotExist, json.JSONDecodeError):
            return None

    def get_state_history(self, session_id: str = None) -> List[Dict[str, Any]]:
        """Get all historical states for a session in chronological order

        Args:
            session_id: Optional session ID. If None, uses current session

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
            # Get all states for this session ordered by timestamp
            states = (
                SessionState.select()
                .where(SessionState.session == session)
                .order_by(SessionState.timestamp.asc())  # Oldest first
            )

            # Parse JSON data for each state
            result = []
            for state in states:
                try:
                    state_data = json.loads(state.state_data)
                    # Add timestamp for reference
                    state_data['timestamp'] = state.timestamp.isoformat()
                    state_data['progress'] = state.progress
                    result.append(state_data)
                except json.JSONDecodeError:
                    continue

            # Restore original session_id
            if session_id:
                self.session_id = current_session_id

            return result
        except Exception:
            # Restore original session_id
            if session_id:
                self.session_id = current_session_id
            return []

    def close_session(self):
        """Close the current session"""
        session = self.get_session(create_if_missing=False)
        if session:
            session.active = False
            session.save()

    def delete_session(self):
        """Delete the current session and all associated states"""
        session = self.get_session(create_if_missing=False)
        if session:
            # First delete states (foreign key constraint)
            SessionState.delete().where(SessionState.session == session).execute()
            # Then delete session
            session.delete_instance()
            self._session = None
            self.session_id = None

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
            print(f"Database file exists: {exists} at {db_path}")

            if exists:
                # Check if it's writable
                writable = os.access(db_path, os.W_OK)
                print(f"Database file is writable: {writable}")

                # Verify table structure
                if Session.table_exists():
                    print("Session table exists")
                if SessionState.table_exists():
                    print("SessionState table exists")

                # Try a test query
                session_count = Session.select().count()
                print(f"Found {session_count} sessions in database")

                return True
            else:
                # Try to create the parent directory if it doesn't exist
                parent_dir = db_path.parent
                if not parent_dir.exists():
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    print(f"Created parent directory: {parent_dir}")

                # Try to create and write to the database
                with open(db_path, 'w') as f:
                    f.write('')
                print(f"Created empty database file at {db_path}")

                # Reconnect database and create tables
                self.db.close()
                self.db.connect()
                self.db.create_tables([Session, SessionState], safe=True)
                print("Created database tables")

                return True
        except Exception as e:
            print(f"Database check error: {e}")
            return False

    def debug_session_info(self, session_id: str = None):
        """Print debug information about a session

        Args:
            session_id: Optional session ID to debug, uses current if None
        """
        target_id = session_id or self.session_id
        if not target_id:
            print("No session_id to debug")
            return

        print(f"\n=== Session Debug Info for {target_id} ===")

        # Check if session exists
        try:
            session = Session.get(Session.id == target_id)
            print(f"Session found: {session.id}")
            print(f"  User ID: {session.user_id}")
            print(f"  Client ID: {session.client_id}")
            print(f"  Form Class: {session.form_class}")
            print(f"  Created: {session.created_at}")
            print(f"  Last Active: {session.last_active}")
            print(f"  Active: {session.active}")

            # Count states
            states = SessionState.select().where(SessionState.session == session)
            state_count = states.count()
            print(f"Session has {state_count} states")

            if state_count > 0:
                # Show latest state
                latest = states.order_by(SessionState.timestamp.desc()).first()
                print(f"Latest state: {latest.timestamp}")
                print(f"Latest progress: {latest.progress}%")
        except DoesNotExist:
            print(f"Session not found with ID: {target_id}")
        except Exception as e:
            print(f"Error getting session debug info: {e}")

        print("=== End Debug Info ===\n")
