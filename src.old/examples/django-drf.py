# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import serializers
# from pydantic import Field
# from drf_pydantic import BaseModel
# from typing import List

# from pydantic2 import PydanticAIClient, ModelSettings


# class FeedbackAnalysis(BaseModel):
#     summary: str = Field(..., description="Summary of the feedback")
#     sentiment: str = Field(..., description="Detected sentiment")
#     key_points: List[str] = Field(..., description="Key points from the feedback")


# class FeedbackSerializer(serializers.Serializer):
#     feedback = FeedbackAnalysis.drf_serializer()


# class FeedbackView(APIView):
#     def post(self, request):
#         feedback = request.data.get('feedback', '')

#         client = PydanticAIClient(
#             model_name="openai/gpt-4o-mini-2024-07-18",
#             client_id="demo_client",
#             user_id=str(request.user.id),
#             verbose=False,
#             retries=3,
#             online=True,
#             max_budget=1,
#             model_settings=ModelSettings(
#                 max_tokens=1000,
#                 temperature=0.7,
#                 top_p=1,
#                 frequency_penalty=0,
#             )
#         )

#         # Set up the conversation with system message
#         client.message_handler.add_message_system(
#             "You are a helpful AI assistant. Be concise but informative."
#         )

#         client.message_handler.add_message_block('FEEDBACK', feedback)

#         response: FeedbackAnalysis = client.generate(
#             result_type=FeedbackAnalysis
#         )

#         serializer = FeedbackSerializer(data={
#             "feedback": response.model_dump()
#         })
#         if serializer.is_valid():
#             return Response(serializer.data)
#         else:
#             return Response(serializer.errors, status=400)
