from typing import Dict, Any


class UsageInfo:
    """
    Class for handling usage information retrieval and display.
    This class provides methods to get and print usage information for LLM API calls.
    """

    def __init__(self, client):
        """
        Initialize the UsageInfo class with a reference to the LiteLLM client.

        Args:
            client: Reference to the LiteLLM client instance
        """
        from ..litellm_client import LiteLLMClient
        self.client: LiteLLMClient = client

    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get comprehensive usage information for the last request.

        Returns:
            Dictionary with token counts, costs, and other usage information
        """
        usage_info = {
            "model": self.client.meta.model_used,
            "response_time_seconds": self.client.meta.response_time_seconds,
            "token_count": self.client.meta.token_count,
            "max_tokens_for_model": self.client.get_max_tokens_for_model(),
        }

        # Get cost directly from _hidden_params if available
        if (self.client.last_response
                and hasattr(self.client.last_response, '_hidden_params')):
            hidden_params = getattr(self.client.last_response, '_hidden_params', {})
            if 'response_cost' in hidden_params:
                usage_info["cost_usd"] = hidden_params['response_cost']
        else:
            # Use calculate_cost as fallback
            usage_info["cost_usd"] = self.client.calculate_cost()

        # Add token breakdown if available
        if self.client.last_response and hasattr(self.client.last_response, 'usage'):
            usage = getattr(self.client.last_response, 'usage', None)
            if usage:
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)

                # If prompt/completion tokens are not available but total_tokens is,
                # use heuristic to estimate the split
                if (prompt_tokens == 0 and completion_tokens == 0
                        and self.client.meta.token_count):
                    # Use more accurate heuristic: count tokens in request
                    prompt_tokens = self.client.count_tokens()
                    completion_tokens = self.client.meta.token_count - prompt_tokens
                    # Protect against negative values
                    if completion_tokens < 0:
                        completion_tokens = 0

                prompt_cost, completion_cost = self.client.get_token_cost(
                    prompt_tokens, completion_tokens
                )

                usage_info.update({
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "prompt_cost_usd": prompt_cost,
                    "completion_cost_usd": completion_cost
                })

        return usage_info

    def print_usage_info(self) -> None:
        """
        Print usage information for the last request.

        Args:
            usage_info: Optional pre-fetched usage information. If None, will fetch it.
        """
        usage_info = self.get_usage_info()

        # Try to get cost information through the API
        try:
            print("\n=== API Usage Information ===")

            # Basic information
            print(f"\nModel: {usage_info.get('model', 'Unknown')}")
            print(
                f"Response time: {usage_info.get('response_time_seconds', 0):.3f} sec"
            )

            # Display input/output token counts and costs
            prompt_tokens = usage_info.get('prompt_tokens', 0)
            completion_tokens = usage_info.get('completion_tokens', 0)
            print(f"Input tokens: {prompt_tokens}")
            print(f"Output tokens: {completion_tokens}")

            # Cost information
            print("\n--- Cost Information ---")
            total_cost = usage_info.get('cost_usd', 0)
            prompt_cost = usage_info.get('prompt_cost_usd', 0)
            completion_cost = usage_info.get('completion_cost_usd', 0)

            # Calculate cost per token
            input_cost_per_token = (
                prompt_cost / prompt_tokens if prompt_tokens > 0 else 0
            )
            output_cost_per_token = (
                completion_cost / completion_tokens if completion_tokens > 0 else 0
            )

            print(
                f"Input token cost: ${prompt_cost:.6f} "
                f"(${input_cost_per_token:.8f}/token)"
            )
            print(
                f"Output token cost: ${completion_cost:.6f} "
                f"(${output_cost_per_token:.8f}/token)"
            )
            print(f"Total request cost: ${total_cost:.6f}")

            # Additional information
            print(
                f"\nMax tokens for model: {usage_info.get('max_tokens_for_model', 0)}"
            )

            # Get updated budget information after the request
            budget_info = self.client.get_budget_info()
            print("\n=== Updated Budget Information ===")
            for key, value in budget_info.items():
                if isinstance(value, float):
                    if key == "budget_used_percent":
                        print(f"{key}: {value:.2f}%")
                    else:
                        print(f"{key}: ${value:.6f}")
                else:
                    print(f"{key}: {value}")

        except Exception as usage_err:
            print(f"\nCould not get API usage information: {usage_err}")
            print("Reason: Some providers may not return complete information")
