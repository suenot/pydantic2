# Installation

## Requirements

- Python 3.8 or higher
- OpenRouter API key (for model access)
- Internet connection (for online search feature)

## Installing Pydantic2

### Using pip

```bash
pip install pydantic2
```

### From source

```bash
git clone https://github.com/markolofsen/pydantic2.git
cd pydantic2
pip install -e .
```

## API Key Setup

Pydantic2 uses OpenRouter as its default model provider. You'll need to set up your API key:

### Environment Variable

```bash
export OPENROUTER_API_KEY=your_api_key_here
```

### In your code

```python
from pydantic2 import PydanticAIClient

client = PydanticAIClient(
    api_key="your_api_key_here"
)
```

## Verifying Installation

Create a test script to verify your installation:

```python
from pydantic2 import PydanticAIClient
from pydantic import BaseModel, Field

class TestResponse(BaseModel):
    message: str = Field(description="Test message")

client = PydanticAIClient(verbose=True)

# Add a simple test message
client.message_handler.add_message_user("Hello, world!")

# Generate response
response: TestResponse = client.generate(result_type=TestResponse)
print(response.message)
```

## Optional Dependencies

### For async support
```bash
pip install aiohttp
```

### For colored logging
```bash
pip install colorlog
```

### For development
```bash
pip install -e ".[dev]"
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```python
   # Set API key in code
   client = PydanticAIClient(api_key="your_api_key")
   ```

2. **Model Not Found**
   ```python
   # Specify full model name
   client = PydanticAIClient(
       model_name="openai/gpt-4o-mini"
   )
   ```

3. **Budget Errors**
   ```python
   # Set appropriate budget
   client = PydanticAIClient(max_budget=10.0)
   ```

### Getting Help

- Check our [GitHub Issues](https://github.com/markolofsen/pydantic2/issues)
- Email support: support@unrealos.com

## Next Steps

- [Quick Start Guide](quick-start.md)
- [Configuration Guide](configuration.md)
- [Basic Usage Examples](../examples/basic-usage.md)
