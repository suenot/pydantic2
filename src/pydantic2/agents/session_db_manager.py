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


class FormState(BaseModel):
    """Model for tracking form states within a session"""
    id = AutoField()
    session = ForeignKeyField(Session, backref='form_states')
    state_data = TextField()
    progress = TextField(null=True)
    timestamp = DateTimeField(default=datetime.now)


class ChatMessage(BaseModel):
    """Model for tracking chat messages within a session"""
    id = AutoField()
    session = ForeignKeyField(Session, backref='chat_messages')
    role = CharField()  # 'user' or 'assistant'
    content = TextField()
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
        self.db.create_tables([Session, FormState, ChatMessage], safe=True)

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
            state = FormState.create(
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
                FormState.select()
                .where(FormState.session == self._session)
                .order_by(FormState.timestamp.desc())
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
            List of state dictionaries in chronological order
        """
        if session_id:
            self.set_session(session_id)

        if not self._session:
            self._log("No active session to get history for", "warning")
            return []

        try:
            # Get chat messages
            messages = (
                ChatMessage.select()
                .where(ChatMessage.session == self._session)
                .order_by(ChatMessage.timestamp.asc())
            )

            if limit:
                messages = messages.limit(limit)

            # Format messages
            history = []
            for message in messages:
                history.append({
                    'role': message.role,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'session_id': self._session.id
                })

            self._log(f"Retrieved {len(history)} messages for session {self._session.id}")
            return history
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
            # Delete chat messages first
            ChatMessage.delete().where(ChatMessage.session == self._session).execute()
            # Delete form states
            FormState.delete().where(FormState.session == self._session).execute()
            # Then delete session
            self._session.delete_instance()
            self._session = None
            self._log("Deleted session and associated data")

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

                if Session.table_exists() and FormState.table_exists() and ChatMessage.table_exists():
                    self._log("Database tables exist")
                    return True
            else:
                # Create database and tables
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.db.close()
                self.db.connect()
                self.db.create_tables([Session, FormState, ChatMessage], safe=True)
                self._log("Created database and tables")
                return True

        except Exception as e:
            self._log(f"Database check error: {e}", "error")
            return False

    def set_verbose(self, verbose: bool):
        """Set verbosity level"""
        self.verbose = verbose
        logger.setLevel(logging.INFO if verbose else logging.WARNING)

    def save_chat_message(self, role: str, content: str) -> bool:
        """Save a chat message to the session history

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            bool: True if message was saved successfully
        """
        if not self._session:
            self._log("No active session to save message to", "warning")
            return False

        try:
            # Create new chat message record
            message = ChatMessage.create(
                session=self._session,
                role=role,
                content=content,
                timestamp=datetime.now()
            )

            # Update session activity
            self._session.last_active = datetime.now()
            self._session.save()

            self._log(f"Saved chat message for session {self._session.id}")
            return True
        except Exception as e:
            self._log(f"Error saving chat message: {e}", "error")
            return False

    def initialize_session(self, user_id: str, client_id: str, form_class: str) -> bool:
        """Initialize a new session with initial state

        Args:
            user_id: User ID
            client_id: Client ID
            form_class: Form class name

        Returns:
            bool: True if initialization was successful
        """
        try:
            # Create new session
            session = self.create_session(
                user_id=user_id,
                client_id=client_id,
                form_class=form_class
            )

            if not session:
                self._log("Failed to create session", "error")
                return False

            # Save initial state
            initial_state = {
                'form': {},
                'progress': 0,
                'prev_question': '',
                'prev_answer': '',
                'feedback': '',
                'confidence': 0.0,
                'next_question': 'Tell me about your startup idea.',
                'next_question_explanation': ''
            }
            self.save_state(initial_state)

            # Save initial question as assistant message
            self.save_chat_message('assistant', initial_state['next_question'])

            self._log("Successfully initialized session")
            return True
        except Exception as e:
            self._log(f"Error initializing session: {e}", "error")
            return False

    def restore_session_state(self, form_class: type) -> Optional[Dict[str, Any]]:
        """Restore the latest state for the current session

        Args:
            form_class: Form class to restore state for

        Returns:
            Optional[Dict[str, Any]]: Restored state or None if failed
        """
        if not self._session:
            self._log("No active session to restore state for", "warning")
            return None

        try:
            state_data = self.get_latest_state()
            if not state_data:
                self._log("No state found to restore", "warning")
                return None

            # Create form instance from state data
            form_data = state_data.get('form', {})
            form = form_class(**form_data)

            # Create state with restored form
            state = {
                'form': form,
                'progress': state_data.get('progress', 0),
                'prev_question': state_data.get('prev_question', ''),
                'prev_answer': state_data.get('prev_answer', ''),
                'feedback': state_data.get('feedback', ''),
                'confidence': state_data.get('confidence', 0.0),
                'next_question': state_data.get('next_question', ''),
                'next_question_explanation': state_data.get('next_question_explanation', '')
            }

            self._log("Successfully restored session state")
            return state
        except Exception as e:
            self._log(f"Error restoring session state: {e}", "error")
            return None

    def process_message(self, message: str, form_class: type) -> Optional[Dict[str, Any]]:
        """Process a message and update session state

        Args:
            message: User's message to process
            form_class: Form class to update state for

        Returns:
            Optional[Dict[str, Any]]: Updated state or None if failed
        """
        if not self._session:
            self._log("No active session to process message for", "warning")
            return None

        try:
            # Save user's message
            self.save_chat_message('user', message)
            self._log(f"Saved user message: {message}")

            # Get current state
            current_state = self.restore_session_state(form_class)
            if not current_state:
                self._log("Failed to get current state", "error")
                return None

            # Update state with new message
            current_state['prev_question'] = current_state['next_question']
            current_state['prev_answer'] = message

            # Save updated state
            self.save_state(current_state)

            self._log("Successfully processed message")
            return current_state
        except Exception as e:
            self._log(f"Error processing message: {e}", "error")
            return None

    def save_assistant_response(self, response: str, state: Dict[str, Any]) -> bool:
        """Save assistant's response and update state

        Args:
            response: Assistant's response
            state: Current state to update

        Returns:
            bool: True if save was successful
        """
        if not self._session:
            self._log("No active session to save response for", "warning")
            return False

        try:
            # Save assistant's response
            self.save_chat_message('assistant', response)
            self._log(f"Saved assistant response: {response}")

            # Update state with response
            state['next_question'] = response
            self.save_state(state)

            self._log("Successfully saved assistant response")
            return True
        except Exception as e:
            self._log(f"Error saving assistant response: {e}", "error")
            return False

    def get_session_messages(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all messages for the current session

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of message dictionaries in chronological order
        """
        if not self._session:
            self._log("No active session to get messages for", "warning")
            return []

        try:
            # Get chat messages
            messages = (
                ChatMessage.select()
                .where(ChatMessage.session == self._session)
                .order_by(ChatMessage.timestamp.asc())
            )

            if limit:
                messages = messages.limit(limit)

            # Format messages
            history = []
            for message in messages:
                history.append({
                    'role': message.role,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'session_id': self._session.id
                })

            self._log(f"Retrieved {len(history)} messages for session {self._session.id}")
            return history
        except Exception as e:
            self._log(f"Error getting session messages: {e}", "error")
            return []
