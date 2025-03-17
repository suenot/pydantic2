# Agent System Example

This example demonstrates how to use Pydantic2's agent system to create AI agents with specific capabilities.

## Basic Agent Example

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List
import datetime

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list)

@tool("get_time", "Get the current time")
def get_current_time() -> str:
    """Get the current time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool("process_text", "Convert text to uppercase")
def process_text(text: str) -> str:
    """Process text input."""
    return text.upper()

# Create and configure the agent
agent = SimpleAgent(model_id="openrouter/openai/gpt-4o-mini")
agent.add_tools([get_current_time, process_text])

# Run the agent
result = agent.run("What time is it and convert 'hello world' to uppercase")
print(result)
```

## Advanced Agent Example

Here's a more advanced example that demonstrates how to create an agent with multiple tools and a custom response model:

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
import requests
import json

class WeatherInfo(BaseModel):
    temperature: float = Field(..., description="Temperature in Celsius")
    conditions: str = Field(..., description="Weather conditions")
    humidity: float = Field(..., description="Humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in km/h")

class ResearchResult(BaseModel):
    topic: str = Field(..., description="The research topic")
    summary: str = Field(..., description="Summary of the research")
    key_points: List[str] = Field(..., description="Key points from the research")
    sources: List[str] = Field(default_factory=list, description="Sources used in the research")

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer to the user's query")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
    weather_info: Optional[WeatherInfo] = Field(None, description="Weather information if requested")
    research_results: Optional[ResearchResult] = Field(None, description="Research results if requested")

@tool("get_time", "Get the current time")
def get_current_time() -> str:
    """Get the current time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool("get_weather", "Get the current weather for a location")
def get_weather(location: str) -> dict:
    """Get the current weather for a location."""
    # This is a mock implementation
    # In a real application, you would use a weather API
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

@tool("search_web", "Search the web for information")
def search_web(query: str) -> List[dict]:
    """Search the web for information."""
    # This is a mock implementation
    # In a real application, you would use a search API
    search_results = {
        "climate change": [
            {"title": "Climate Change: Causes and Effects", "url": "https://example.com/climate-change"},
            {"title": "Global Warming: The Science", "url": "https://example.com/global-warming"},
            {"title": "Climate Action: What You Can Do", "url": "https://example.com/climate-action"}
        ],
        "artificial intelligence": [
            {"title": "AI: An Introduction", "url": "https://example.com/ai-intro"},
            {"title": "Machine Learning Basics", "url": "https://example.com/ml-basics"},
            {"title": "The Future of AI", "url": "https://example.com/ai-future"}
        ]
    }

    # Return some default results if the query is not found
    return search_results.get(query.lower(), [
        {"title": f"Result 1 for {query}", "url": f"https://example.com/result1-{query}"},
        {"title": f"Result 2 for {query}", "url": f"https://example.com/result2-{query}"},
        {"title": f"Result 3 for {query}", "url": f"https://example.com/result3-{query}"}
    ])

@tool("calculate", "Perform a calculation")
def calculate(expression: str) -> float:
    """Perform a calculation."""
    try:
        # Warning: eval can be dangerous in production code
        # This is just for demonstration purposes
        return eval(expression)
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    # Create and configure the agent
    agent = SimpleAgent(
        model_id="openrouter/openai/gpt-4o-mini",
        response_model=AgentResponse
    )

    # Add tools
    agent.add_tools([
        get_time,
        get_weather,
        search_web,
        calculate
    ])

    # Run the agent with different queries
    queries = [
        "What time is it now?",
        "What's the weather like in Tokyo?",
        "Research climate change and summarize the key points.",
        "Calculate the square root of 144 and then add 10 to it."
    ]

    for query in queries:
        print(f"\n\nQuery: {query}")
        print("-" * 50)

        result = agent.run(query)

        print(f"Answer: {result.answer}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Tools used: {', '.join(result.tools_used)}")

        if result.weather_info:
            weather = result.weather_info
            print("\nWeather Information:")
            print(f"Temperature: {weather.temperature}°C")
            print(f"Conditions: {weather.conditions}")
            print(f"Humidity: {weather.humidity}%")
            print(f"Wind Speed: {weather.wind_speed} km/h")

        if result.research_results:
            research = result.research_results
            print("\nResearch Results:")
            print(f"Topic: {research.topic}")
            print(f"Summary: {research.summary}")
            print("\nKey Points:")
            for point in research.key_points:
                print(f"- {point}")
            if research.sources:
                print("\nSources:")
                for source in research.sources:
                    print(f"- {source}")

if __name__ == "__main__":
    main()
```

## Gradio UI Example

You can also launch a Gradio UI for your agent:

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List
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

# Launch Gradio UI
agent.launch_gradio_ui(
    title="Pydantic2 Agent Demo",
    description="Ask questions and the agent will answer using its tools.",
    theme="default",
    share=True
)
```

## Creating Custom Tools

You can create custom tools for your agent:

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List, Optional
import requests
import json

class StockInfo(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_percent: float = Field(..., description="Price change percentage")

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list)
    stock_info: Optional[StockInfo] = Field(None, description="Stock information if requested")

@tool("get_stock_price", "Get the current stock price")
def get_stock_price(symbol: str) -> dict:
    """Get the current stock price for a symbol."""
    # This is a mock implementation
    # In a real application, you would use a stock API
    stock_data = {
        "AAPL": {
            "symbol": "AAPL",
            "price": 150.25,
            "change": 2.75,
            "change_percent": 1.86
        },
        "MSFT": {
            "symbol": "MSFT",
            "price": 290.50,
            "change": -1.25,
            "change_percent": -0.43
        },
        "GOOGL": {
            "symbol": "GOOGL",
            "price": 2750.75,
            "change": 15.50,
            "change_percent": 0.57
        }
    }

    return stock_data.get(symbol.upper(), {
        "symbol": symbol.upper(),
        "price": 100.00,
        "change": 0.00,
        "change_percent": 0.00
    })

# Create and configure the agent
agent = SimpleAgent(
    model_id="openrouter/openai/gpt-4o-mini",
    response_model=AgentResponse
)

# Add tools
agent.add_tools([get_stock_price])

# Run the agent
result = agent.run("What's the current price of AAPL stock?")
print(result)
```

## Key Features

The agent system provides several key features:

1. **Tool Decorator**: The `@tool` decorator makes it easy to define tools.
2. **Type Safety**: Tools and responses are type-safe with Pydantic models.
3. **Gradio UI**: You can launch a Gradio UI for your agent.
4. **Custom Response Models**: You can define custom response models for your agent.
5. **Multiple Tools**: You can add multiple tools to your agent.

## Next Steps

Now that you've seen how to use Pydantic2's agent system, check out the [API Reference](../api/client.md) to learn more about the available APIs.
