# Installation

## Requirements

Pydantic2 requires Python 3.7 or later.

## Installing with pip

```bash
pip install pydantic2
```

## API Keys

Pydantic2 uses OpenRouter as the default model provider. You'll need to set up your API key:

```bash
export OPENROUTER_API_KEY=your_api_key_here
```

You can get an API key from [OpenRouter](https://openrouter.ai/).

Alternatively, you can set the API key in your code:

```python
import os
os.environ["OPENROUTER_API_KEY"] = "your_api_key_here"
```

## Verifying Installation

You can verify that Pydantic2 is installed correctly by running:

```python
import pydantic2
print(pydantic2.__version__)
```

## Next Steps

Once you have Pydantic2 installed, check out the [Quick Start](quick-start.md) guide to learn how to use it.
