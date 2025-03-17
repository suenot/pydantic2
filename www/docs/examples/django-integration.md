# Django Integration Example

This example demonstrates how to integrate Pydantic2 with Django REST framework.

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import Request, LiteLLMClient

class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")

class FeedbackResponseSerializer(serializers.Serializer):
    answer = FeedbackAnalysis.drf_serializer()

class FeedbackView(APIView):
    def post(self, request):
        feedback = request.data.get('feedback', '')

        client = LiteLLMClient(Request(
            model="openrouter/openai/gpt-4o-mini-2024-07-18",
            temperature=0.3,
            answer_model=FeedbackAnalysis,
            max_budget=0.01,
            user_id=request.user.id if hasattr(request, 'user') else None,
            client_id="django_feedback_app"
        ))

        client.msg.add_message_system("You are a feedback analysis expert.")
        client.msg.add_message_user(feedback)

        response: FeedbackAnalysis = client.generate_response()

        serializer = FeedbackResponseSerializer(data={
            "answer": response.model_dump()
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
```

Key features:
- Seamless integration with Django REST framework
- Automatic serialization of Pydantic models
- Type-safe response handling
- Built-in validation
- User tracking through Django's authentication system

## Complete Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import Request, LiteLLMClient

class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")

class FeedbackResponseSerializer(serializers.Serializer):
    answer = serializers.JSONField()

class FeedbackView(APIView):
    def post(self, request):
        feedback = request.data.get('feedback', '')

        client = LiteLLMClient(Request(
            model="openrouter/openai/gpt-4o-mini-2024-07-18",
            temperature=0.3,
            answer_model=FeedbackAnalysis,
            max_budget=0.01,
            user_id=request.user.id if hasattr(request, 'user') else None,
            client_id="django_feedback_app"
        ))

        client.msg.add_message_system("You are a feedback analysis expert.")
        client.msg.add_message_user(feedback)

        response: FeedbackAnalysis = client.generate_response()

        serializer = FeedbackResponseSerializer(data={
            "answer": response.model_dump()
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
```

## Step-by-Step Explanation

### 1. Define a Response Model

First, we define a Pydantic model that represents the structure of the response we want:

```python
class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")
```

### 2. Define a Serializer

Next, we define a Django REST framework serializer to handle the response:

```python
class FeedbackResponseSerializer(serializers.Serializer):
    answer = serializers.JSONField()
```

### 3. Create an API View

We create a Django REST framework API view to handle the request:

```python
class FeedbackView(APIView):
    def post(self, request):
        feedback = request.data.get('feedback', '')

        client = LiteLLMClient(Request(
            model="openrouter/openai/gpt-4o-mini-2024-07-18",
            temperature=0.3,
            answer_model=FeedbackAnalysis,
            max_budget=0.01,
            user_id=request.user.id if hasattr(request, 'user') else None,
            client_id="django_feedback_app"
        ))

        client.msg.add_message_system("You are a feedback analysis expert.")
        client.msg.add_message_user(feedback)

        response: FeedbackAnalysis = client.generate_response()

        serializer = FeedbackResponseSerializer(data={
            "answer": response.model_dump()
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
```

## Complete Django Project Example

Here's a more complete example of a Django project that uses Pydantic2:

### models.py

```python
from django.db import models
from django.contrib.auth.models import User

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user or 'Anonymous'} at {self.created_at}"

class FeedbackAnalysisResult(models.Model):
    feedback = models.OneToOneField(Feedback, on_delete=models.CASCADE, related_name='analysis')
    summary = models.TextField()
    sentiment = models.CharField(max_length=50)
    key_points = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.feedback}"
```

### serializers.py

```python
from rest_framework import serializers
from .models import Feedback, FeedbackAnalysisResult

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'text', 'created_at']
        read_only_fields = ['created_at']

class FeedbackAnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackAnalysisResult
        fields = ['id', 'summary', 'sentiment', 'key_points', 'created_at']
        read_only_fields = ['created_at']

class FeedbackWithAnalysisSerializer(serializers.ModelSerializer):
    analysis = FeedbackAnalysisResultSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'text', 'created_at', 'analysis']
        read_only_fields = ['created_at']
```

### views.py

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import Request, LiteLLMClient

from .models import Feedback, FeedbackAnalysisResult
from .serializers import FeedbackSerializer, FeedbackWithAnalysisSerializer

class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")

class FeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        feedbacks = Feedback.objects.filter(user=request.user)
        serializer = FeedbackWithAnalysisSerializer(feedbacks, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.save(user=request.user)

            # Analyze the feedback using Pydantic2
            client = LiteLLMClient(Request(
                model="openrouter/openai/gpt-4o-mini-2024-07-18",
                temperature=0.3,
                answer_model=FeedbackAnalysis,
                max_budget=0.01,
                user_id=str(request.user.id),
                client_id="django_feedback_app"
            ))

            client.msg.add_message_system("You are a feedback analysis expert.")
            client.msg.add_message_user(feedback.text)

            response: FeedbackAnalysis = client.generate_response()

            # Save the analysis result
            analysis = FeedbackAnalysisResult.objects.create(
                feedback=feedback,
                summary=response.summary,
                sentiment=response.sentiment,
                key_points=response.key_points
            )

            # Return the feedback with analysis
            result_serializer = FeedbackWithAnalysisSerializer(feedback)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### urls.py

```python
from django.urls import path
from .views import FeedbackView

urlpatterns = [
    path('feedback/', FeedbackView.as_view(), name='feedback'),
]
```

## Key Features

The Django integration example demonstrates several key features:

1. **Seamless integration with Django REST framework**: Pydantic2 works well with Django's serialization system.
2. **User tracking**: The example uses Django's authentication system to track users.
3. **Database integration**: The example saves the analysis results to a database.
4. **Structured responses**: The example uses Pydantic models to define the structure of the response.
5. **Budget management**: The example sets a budget limit for each request.

## Next Steps

Now that you've seen how to integrate Pydantic2 with Django, check out the [FastAPI Integration](fastapi-integration.md) example to learn how to integrate Pydantic2 with FastAPI.
