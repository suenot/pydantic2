# Agents API Reference

This page provides detailed information about the agents API in Pydantic2.

## SimpleAgent

The `SimpleAgent` class is the main class for creating AI agents with specific capabilities.

### Constructor

```python
def __init__(
    self,
    model_id: str = "openrouter/openai/gpt-4o-mini",
    response_model: Type[BaseModel] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    verbose: bool = False
):
    """Initialize the SimpleAgent with configuration parameters."""
```

#### Parameters

- `model_id` (`str`): The model identifier. Default: `"openrouter/openai/gpt-4o-mini"`.
- `response_model` (`Type[BaseModel]`, optional): The Pydantic model for responses. If not provided, a default model will be used.
- `temperature` (`float`): The temperature for response randomness (0.0-1.0). Default: `0.7`.
- `max_tokens` (`int`): The maximum number of tokens in the response. Default: `1000`.
- `verbose` (`bool`): Whether to show detailed output. Default: `False`.

### Methods

#### add_tools

```python
def add_tools(self, tools: List[Callable]) -> None:
    """Add tools to the agent."""
```

Adds tools to the agent.

**Parameters**:
- `tools` (`List[Callable]`): A list of tool functions.

**Example**:
```python
agent.add_tools([get_time, process_text])
```

#### run

```python
def run(self, query: str) -> Any:
    """Run the agent with a query."""
```

Runs the agent with a query.

**Parameters**:
- `query` (`str`): The query to run the agent with.

**Returns**:
- An instance of the response model.

**Example**:
```python
result = agent.run("What time is it?")
```

#### launch_gradio_ui

```python
def launch_gradio_ui(
    self,
    title: str = "Pydantic2 Agent",
    description: str = "Ask a question and the agent will answer using its tools.",
    theme: str = "default",
    share: bool = False
) -> None:
    """Launch a Gradio UI for the agent."""
```

Launches a Gradio UI for the agent.

**Parameters**:
- `title` (`str`): The title of the UI. Default: `"Pydantic2 Agent"`.
- `description` (`str`): The description of the UI. Default: `"Ask a question and the agent will answer using its tools."`.
- `theme` (`str`): The theme of the UI. Default: `"default"`.
- `share` (`bool`): Whether to share the UI. Default: `False`.

**Example**:
```python
agent.launch_gradio_ui(
    title="My Agent",
    description="Ask me anything!",
    theme="default",
    share=True
)
```

## tool

The `tool` decorator is used to define tools for the agent.

```python
def tool(name: str, description: str) -> Callable:
    """Decorator for defining a tool."""
```

#### Parameters

- `name` (`str`): The name of the tool.
- `description` (`str`): The description of the tool.

**Returns**:
- A decorator function.

**Example**:
```python
@tool("get_time", "Get the current time")
def get_current_time() -> str:
    """Get the current time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

## Response Models

### AgentResponse

The `AgentResponse` class is the default response model for the agent.

```python
class AgentResponse(BaseModel):
    """Default response model for the agent."""
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
```

#### Fields

- `answer` (`str`): The main answer.
- `reasoning` (`str`): The reasoning process.
- `tools_used` (`List[str]`): A list of tools used.

## Custom Response Models

You can define custom response models for the agent:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class WeatherInfo(BaseModel):
    temperature: float = Field(..., description="Temperature in Celsius")
    conditions: str = Field(..., description="Weather conditions")
    humidity: float = Field(..., description="Humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in km/h")

class CustomAgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
    weather_info: Optional[WeatherInfo] = Field(None, description="Weather information if requested")
```

## Complete Example

Here's a complete example of using the agents API:

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
import random

class WeatherInfo(BaseModel):
    temperature: float = Field(..., description="Temperature in Celsius")
    conditions: str = Field(..., description="Weather conditions")
    humidity: float = Field(..., description="Humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in km/h")

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list)
    weather_info: Optional[WeatherInfo] = Field(None, description="Weather information if requested")

@tool("get_time", "Get the current time")
def get_current_time() -> str:
    """Get the current time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool("get_weather", "Get the current weather for a location")
def get_weather(location: str) -> dict:
    """Get the current weather for a location."""
    # This is a mock implementation
    weather_data = {
        "New York": {
            "temperature": 22.5,
            "conditions": "Partly cloudy",
            "humidity": 65.0,
            "wind_speed": 10.2
        },
        "London": {
            "temperature": 18.0,
            "conditions": "Rainy",
            "humidity": 80.0,
            "wind_speed": 15.5
        },
        "Tokyo": {
            "temperature": 28.0,
            "conditions": "Sunny",
            "humidity": 70.0,
            "wind_speed": 8.0
        }
    }

    return weather_data.get(location, {
        "temperature": 20.0,
        "conditions": "Unknown",
        "humidity": 50.0,
        "wind_speed": 5.0
    })

@tool("roll_dice", "Roll a dice with the specified number of sides")
def roll_dice(sides: int = 6) -> int:
    """Roll a dice with the specified number of sides."""
    return random.randint(1, sides)

# Create and configure the agent
agent = SimpleAgent(
    model_id="openrouter/openai/gpt-4o-mini",
    response_model=AgentResponse
)

# Add tools
agent.add_tools([
    get_time,
    get_weather,
    roll_dice
])

# Run the agent
result = agent.run("What's the weather like in Tokyo?")
print(result)

# Launch Gradio UI
agent.launch_gradio_ui(
    title="Weather Agent",
    description="Ask about the weather in different cities.",
    theme="default",
    share=True
)
```
