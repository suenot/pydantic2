# FastAPI Integration Example

This example demonstrates how to integrate Pydantic2 with FastAPI to create a text analysis API.

## Complete Example

```python
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

from pydantic2 import LiteLLMClient, Request

# Define a response model
class TextAnalysis(BaseModel):
    """Model for text analysis results."""
    summary: str = Field(description="Summary of the text")
    topics: List[str] = Field(description="Main topics in the text")
    sentiment: str = Field(description="Overall sentiment of the text")
    key_phrases: List[str] = Field(description="Key phrases extracted from the text")
    reading_time: int = Field(description="Estimated reading time in minutes")
    language: str = Field(description="Detected language of the text")

# Create a FastAPI app
app = FastAPI(
    title="Text Analysis API",
    description="API for analyzing text using Pydantic2",
    version="1.0.0"
)

# Create a shared client for reuse
def get_client(user_id: str = None):
    """Get a LiteLLMClient instance."""
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.3,
        max_tokens=500,
        answer_model=TextAnalysis,
        max_budget=0.01,
        user_id=user_id,
        client_id="fastapi_text_analysis",
        verbose=False
    )
    return LiteLLMClient(config)

@app.post("/analyze", response_model=TextAnalysis)
async def analyze_text(
    text: str,
    user_id: Optional[str] = Query(None, description="User ID for tracking"),
):
    """Analyze text and return structured results."""
    # Generate a user ID if not provided
    if not user_id:
        user_id = str(uuid.uuid4())

    # Get a client
    client = get_client(user_id)

    # Add messages
    client.msg.add_message_system("You are a text analysis expert. Analyze the following text.")
    client.msg.add_message_user(text)

    try:
        # Generate a response
        response: TextAnalysis = client.generate_response()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/{user_id}")
async def get_usage(user_id: str):
    """Get usage statistics for a user."""
    client = get_client(user_id)
    try:
        usage_data = client.usage_tracker.get_client_usage_data(client_id="fastapi_text_analysis")
        return {
            "user_id": user_id,
            "total_requests": usage_data.total_requests,
            "successful_requests": usage_data.successful_requests,
            "failed_requests": usage_data.failed_requests,
            "total_cost": usage_data.total_cost,
            "models_used": [model.model_name for model in usage_data.models_used]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/request/{request_id}")
async def get_request_details(request_id: str):
    """Get details for a specific request."""
    client = get_client()
    try:
        request_details = client.usage_tracker.get_request_details(request_id=request_id)
        if not request_details:
            raise HTTPException(status_code=404, detail="Request not found")
        return request_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Step-by-Step Explanation

### 1. Define a Response Model

First, we define a Pydantic model that represents the structure of the response we want:

```python
class TextAnalysis(BaseModel):
    """Model for text analysis results."""
    summary: str = Field(description="Summary of the text")
    topics: List[str] = Field(description="Main topics in the text")
    sentiment: str = Field(description="Overall sentiment of the text")
    key_phrases: List[str] = Field(description="Key phrases extracted from the text")
    reading_time: int = Field(description="Estimated reading time in minutes")
    language: str = Field(description="Detected language of the text")
```

### 2. Create a FastAPI App

Next, we create a FastAPI app:

```python
app = FastAPI(
    title="Text Analysis API",
    description="API for analyzing text using Pydantic2",
    version="1.0.0"
)
```

### 3. Create a Client Factory

We create a function to get a client instance:

```python
def get_client(user_id: str = None):
    """Get a LiteLLMClient instance."""
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.3,
        max_tokens=500,
        answer_model=TextAnalysis,
        max_budget=0.01,
        user_id=user_id,
        client_id="fastapi_text_analysis",
        verbose=False
    )
    return LiteLLMClient(config)
```

### 4. Create API Endpoints

We create API endpoints for analyzing text and getting usage statistics:

```python
@app.post("/analyze", response_model=TextAnalysis)
async def analyze_text(
    text: str,
    user_id: Optional[str] = Query(None, description="User ID for tracking"),
):
    """Analyze text and return structured results."""
    # Generate a user ID if not provided
    if not user_id:
        user_id = str(uuid.uuid4())

    # Get a client
    client = get_client(user_id)

    # Add messages
    client.msg.add_message_system("You are a text analysis expert. Analyze the following text.")
    client.msg.add_message_user(text)

    try:
        # Generate a response
        response: TextAnalysis = client.generate_response()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/{user_id}")
async def get_usage(user_id: str):
    """Get usage statistics for a user."""
    client = get_client(user_id)
    try:
        usage_data = client.usage_tracker.get_client_usage_data(client_id="fastapi_text_analysis")
        return {
            "user_id": user_id,
            "total_requests": usage_data.total_requests,
            "successful_requests": usage_data.successful_requests,
            "failed_requests": usage_data.failed_requests,
            "total_cost": usage_data.total_cost,
            "models_used": [model.model_name for model in usage_data.models_used]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/request/{request_id}")
async def get_request_details(request_id: str):
    """Get details for a specific request."""
    client = get_client()
    try:
        request_details = client.usage_tracker.get_request_details(request_id=request_id)
        if not request_details:
            raise HTTPException(status_code=404, detail="Request not found")
        return request_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Complete FastAPI Project Example

Here's a more complete example of a FastAPI project that uses Pydantic2:

### models.py

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TextAnalysisRequest(BaseModel):
    """Request model for text analysis."""
    text: str = Field(..., description="Text to analyze")
    user_id: Optional[str] = Field(None, description="User ID for tracking")

class TextAnalysis(BaseModel):
    """Model for text analysis results."""
    summary: str = Field(description="Summary of the text")
    topics: List[str] = Field(description="Main topics in the text")
    sentiment: str = Field(description="Overall sentiment of the text")
    key_phrases: List[str] = Field(description="Key phrases extracted from the text")
    reading_time: int = Field(description="Estimated reading time in minutes")
    language: str = Field(description="Detected language of the text")

class TextAnalysisResponse(BaseModel):
    """Response model for text analysis."""
    request_id: str = Field(..., description="Request ID")
    timestamp: datetime = Field(..., description="Timestamp of the analysis")
    analysis: TextAnalysis = Field(..., description="Analysis results")
    model_used: str = Field(..., description="Model used for analysis")
    processing_time: float = Field(..., description="Processing time in seconds")

class UsageResponse(BaseModel):
    """Response model for usage statistics."""
    user_id: str = Field(..., description="User ID")
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    total_cost: float = Field(..., description="Total cost in USD")
    models_used: List[str] = Field(..., description="Models used")
```

### dependencies.py

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from typing import Optional

from pydantic2 import LiteLLMClient, Request
from .models import TextAnalysis

# API key security
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY", "test-api-key")  # Default for development

api_key_header = APIKeyHeader(name=API_KEY_NAME)

def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API key."""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": API_KEY_NAME},
        )
    return api_key

def get_client(user_id: Optional[str] = None):
    """Get a LiteLLMClient instance."""
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.3,
        max_tokens=500,
        answer_model=TextAnalysis,
        max_budget=0.01,
        user_id=user_id,
        client_id="fastapi_text_analysis",
        verbose=False
    )
    return LiteLLMClient(config)
```

### main.py

```python
from fastapi import FastAPI, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime

from .models import TextAnalysisRequest, TextAnalysisResponse, UsageResponse
from .dependencies import get_client, verify_api_key

# Create a FastAPI app
app = FastAPI(
    title="Text Analysis API",
    description="API for analyzing text using Pydantic2",
    version="1.0.0"
)

@app.post("/analyze", response_model=TextAnalysisResponse, dependencies=[Depends(verify_api_key)])
async def analyze_text(request: TextAnalysisRequest):
    """Analyze text and return structured results."""
    # Generate a user ID if not provided
    user_id = request.user_id or str(uuid.uuid4())

    # Get a client
    client = get_client(user_id)

    # Add messages
    client.msg.add_message_system("You are a text analysis expert. Analyze the following text.")
    client.msg.add_message_user(request.text)

    try:
        # Record start time
        start_time = datetime.now()

        # Generate a response
        analysis = client.generate_response()

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Create response
        response = TextAnalysisResponse(
            request_id=client.meta.request_id,
            timestamp=datetime.now(),
            analysis=analysis,
            model_used=client.meta.model_used,
            processing_time=processing_time
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/{user_id}", response_model=UsageResponse, dependencies=[Depends(verify_api_key)])
async def get_usage(user_id: str):
    """Get usage statistics for a user."""
    client = get_client(user_id)
    try:
        usage_data = client.usage_tracker.get_client_usage_data(client_id="fastapi_text_analysis")
        return UsageResponse(
            user_id=user_id,
            total_requests=usage_data.total_requests,
            successful_requests=usage_data.successful_requests,
            failed_requests=usage_data.failed_requests,
            total_cost=usage_data.total_cost,
            models_used=[model.model_name for model in usage_data.models_used]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/request/{request_id}", dependencies=[Depends(verify_api_key)])
async def get_request_details(request_id: str):
    """Get details for a specific request."""
    client = get_client()
    try:
        request_details = client.usage_tracker.get_request_details(request_id=request_id)
        if not request_details:
            raise HTTPException(status_code=404, detail="Request not found")
        return request_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Key Features

The FastAPI integration example demonstrates several key features:

1. **Seamless integration with FastAPI**: Pydantic2 works well with FastAPI's type system.
2. **User tracking**: The example uses user IDs to track usage.
3. **API key authentication**: The example uses API keys for authentication.
4. **Structured responses**: The example uses Pydantic models to define the structure of the response.
5. **Budget management**: The example sets a budget limit for each request.
6. **Usage tracking**: The example provides endpoints for tracking usage.

## Next Steps

Now that you've seen how to integrate Pydantic2 with FastAPI, check out the [Agent System](agent-system.md) example to learn how to use Pydantic2's agent system.
