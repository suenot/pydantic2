# BaseProgressForm - AI-Powered Form Processing System

## Overview

BaseProgressForm is a flexible framework for creating AI-powered interactive forms with automatic progress tracking and dynamic tool orchestration. It provides a base class that can be extended to create specialized form processors for various use cases.

## Core Components

### 1. Base Classes

#### BaseProgressForm
- Abstract base class for form processing
- Handles tool management, state tracking, and orchestration
- Provides core functionality for form processing and analysis

#### FormState
- Generic state container that tracks:
  - Form data and completion progress (0-100%)
  - Question/answer history
  - User feedback
  - Next questions and explanations

### 2. Key Features

#### Tool Management
- Supports multiple processing tools
- Default `process_form` tool for basic form handling
- Extensible with custom analysis tools
- Automatic tool validation and registration

#### Progress Tracking
- Automatic progress calculation based on filled fields
- Non-decreasing progress to ensure forward movement
- Progress-based tool selection and orchestration

#### Test Agent Integration
- Built-in test agent system for form simulation
- Configurable agent personality and behavior
- Automated dialog testing capabilities

## Implementation Example: StartupForm

The `startup_form.py` demonstrates a practical implementation:

```python
class StartupFormProcessor(BaseProgressForm):
    def __init__(self, user_id: str):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm
        )
        self.tools = [self.analyze_startup]
```

### Form Definition
```python
class StartupForm(BaseModel):
    idea_desc: str
    target_mkt: str
    biz_model: str
    team_info: str
```

### Analysis Tool
```python
def analyze_startup(self, message: str) -> StartupFormResponse:
    # Custom analysis logic when form is complete
    ...
```

## How It Works

1. **Initialization**
   - Create form structure using Pydantic models
   - Initialize BaseProgressForm with form class
   - Register processing and analysis tools

2. **Processing Flow**
   - Form starts empty with 0% progress
   - AI processes user input and updates relevant fields
   - Progress automatically updates based on filled fields
   - System selects appropriate tool based on progress:
     - < 100%: Use process_form for gathering information
     - 100%: Trigger final analysis

3. **Tool Orchestration**
   - Progress-based tool selection
   - Automatic state management
   - Error handling and fallback mechanisms

4. **Dialog Management**
   - Dynamic question generation
   - Context-aware responses
   - Progress-based flow control

## Usage Example

```python
# Create processor instance
processor = StartupFormProcessor(user_id="user123")

# Run interactive dialog
processor.run_test_dialog()

# Or process individual messages
state = processor.determine_action(user_message)
```

## Best Practices

1. **Form Design**
   - Keep form fields focused and specific
   - Use clear field descriptions
   - Design for natural conversation flow

2. **Tool Implementation**
   - Implement specific analysis tools
   - Provide clear tool documentation
   - Handle edge cases and errors

3. **Progress Management**
   - Let the system handle progress tracking
   - Don't manually modify progress
   - Use progress for flow control

## Extension Points

1. **Custom Forms**
   - Create specialized form classes
   - Add domain-specific validation
   - Implement custom field types

2. **Analysis Tools**
   - Add specialized analysis tools
   - Implement custom processing logic
   - Create domain-specific responses

3. **Test Agents**
   - Configure custom test personalities
   - Implement specific testing scenarios
   - Add validation rules

## Error Handling

- Graceful error recovery
- State preservation on failure
- Fallback to basic processing
- Detailed error logging

## Logging and Debugging

- Comprehensive logging system
- Configurable verbosity levels
- Tool execution tracking
- State transition logging
