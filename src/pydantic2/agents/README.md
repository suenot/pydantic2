# AI-Powered Form Processing System (@agents)

## Overview

The `@agents` module provides a robust framework for building AI-powered interactive forms with automatic progress tracking, state management, and dynamic tool orchestration. It consists of two main components:

1. `SessionDBManager` - Handles session and state persistence
2. `BaseProgressForm` - Core form processing logic

## Core Components

### 1. SessionDBManager

Manages session and state persistence using SQLite database with Peewee ORM.

```python
from pydantic2.agents.session_db_manager import SessionDBManager

# Initialize manager
db_manager = SessionDBManager(session_id="optional_id", verbose=True)

# Create new session
session = db_manager.create_session(
    user_id="user123",
    client_id="client456",
    form_class="MyForm"
)

# Save state
db_manager.save_state({
    "form": form_data,
    "progress": 25,
    "prev_question": "Question?",
    "prev_answer": "Answer"
})

# Get latest state
latest_state = db_manager.get_latest_state()

# Get state history
history = db_manager.get_state_history()
```

Key features:
- Automatic database initialization
- State caching for performance
- Session isolation
- Concurrent session support
- State history tracking

### 2. BaseProgressForm

Base class for implementing AI-powered form processors.

```python
from pydantic2.agents.progress_form import BaseProgressForm, FormState
from pydantic import BaseModel

# Define form structure
class MyForm(BaseModel):
    field1: str = Field(description="Field 1 description")
    field2: str = Field(description="Field 2 description")

# Create processor
class MyFormProcessor(BaseProgressForm):
    def __init__(self, user_id: str, session_id: str = None):
        super().__init__(
            user_id=user_id,
            client_id="my_form",
            form_class=MyForm,
            verbose=True,
            session_id=session_id
        )

        # Configure test agent
        self.configure_test_agent(
            prompt="Your agent prompt here",
            client=self._get_test_agent_client(temperature=0.7)
        )
```

Key features:
- Automatic progress tracking
- State management
- Test agent integration
- Tool system
- Client pooling

## Implementation Example

Here's a complete example of implementing a form processor:

```python
from pydantic2.agents.progress_form import BaseProgressForm, FormState
from pydantic import BaseModel, Field
from typing import List

# 1. Define form structure
class StartupForm(BaseModel):
    idea_desc: str = Field(default="", description="Description of startup idea")
    target_mkt: str = Field(default="", description="Target market info")
    biz_model: str = Field(default="", description="Business model info")
    team_info: str = Field(default="", description="Team background")

# 2. Create processor
class StartupFormProcessor(BaseProgressForm):
    def __init__(self, user_id: str, session_id: str = None):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm,
            verbose=True,
            session_id=session_id
        )

        # Configure test agent
        self.configure_test_agent(
            prompt="You are a startup founder...",
            client=self._get_test_agent_client(temperature=0.7)
        )

    def _process_with_test_agent(self, message: str) -> FormState:
        # Get response from test agent
        response = self.get_test_agent_response()

        # Update form data based on message
        form_data = self.current_state.form.model_dump()

        # Map messages to form fields
        if "startup idea" in message.lower():
            form_data["idea_desc"] = message
        elif "target market" in message.lower():
            form_data["target_mkt"] = message
        # ... map other fields

        # Create new state
        new_state = FormState[self.form_class](
            form=self.form_class(**form_data),
            progress=self.current_state.progress,
            prev_question=self.current_state.next_question,
            prev_answer=message,
            next_question=response
        )

        # Update progress
        filled_fields = sum(1 for value in form_data.values() if value)
        total_fields = len(form_data)
        new_state.progress = min(100, int((filled_fields / total_fields) * 100))

        return new_state
```

## Usage Examples

### 1. Running a New Dialog

```python
# Create processor
processor = StartupFormProcessor(user_id="user123")

# Run dialog
messages = [
    "I'm building a food delivery app",
    "Target market is urban professionals",
    "Revenue from 10% commission"
]

session_id = processor.run_simple_dialog(messages)
```

### 2. Continuing Existing Session

```python
# Continue dialog
processor.continue_session_dialog(
    session_id="existing_id",
    messages=["Additional message"]
)
```

### 3. Viewing Session History

```python
# Show history
processor.show_session_history(session_id="session_id")
```

## Important Implementation Details

### 1. State Management
- States are automatically saved after each message
- Progress is calculated based on filled fields
- Form data is preserved between sessions
- State history is maintained

### 2. Test Agent Configuration
- Configure test agent with custom prompt
- Set appropriate temperature for responses
- Handle agent responses in `_process_with_test_agent`
- Map responses to form fields

### 3. Form Field Mapping
- Implement field mapping logic in `_process_with_test_agent`
- Use specific conditions for each field
- Update progress based on filled fields
- Handle empty fields appropriately

### 4. Error Handling
- Graceful error recovery
- State preservation on errors
- Proper logging of issues
- Session cleanup on errors

## Best Practices

1. **Form Design**
   - Use clear field descriptions
   - Keep forms focused
   - Design for natural conversation
   - Add appropriate validation

2. **Test Agent**
   - Write clear prompts
   - Set appropriate temperature
   - Handle edge cases
   - Validate responses

3. **State Management**
   - Regular state saving
   - Proper progress calculation
   - Clean session handling
   - Efficient caching

4. **Error Handling**
   - Comprehensive logging
   - Graceful recovery
   - State preservation
   - User feedback

## Performance Considerations

1. **Database**
   - Use efficient queries
   - Implement caching
   - Clean up old sessions
   - Monitor performance

2. **State Management**
   - Minimize state updates
   - Use efficient caching
   - Clean up old states
   - Monitor memory usage

3. **API Calls**
   - Implement rate limiting
   - Use client pooling
   - Handle timeouts
   - Monitor usage

## Logging and Monitoring

1. **Logging Levels**
   - INFO: Normal operations
   - WARNING: Potential issues
   - ERROR: Critical problems
   - DEBUG: Detailed information

2. **Monitoring Points**
   - State transitions
   - Progress updates
   - API calls
   - Error rates
   - Performance metrics
