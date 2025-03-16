"""
Simple Agent - A lightweight implementation of an AI agent with tools
"""

import logging
import os
from typing import Callable, Dict, List, Any, Optional

from smolagents import LiteLLMModel, ToolCallingAgent, GradioUI as OriginalGradioUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Custom GradioUI class to handle None values
class GradioUI(OriginalGradioUI):
    """A wrapper around smolagents GradioUI that handles None values properly"""

    def __init__(self, agent, file_upload_folder=None):
        # Make sure name and description are strings, not None
        if not hasattr(agent, 'name') or agent.name is None:
            agent.name = "Agent"
        if not hasattr(agent, 'description') or agent.description is None:
            agent.description = ""

        # Call the parent constructor
        super().__init__(agent, file_upload_folder)


class SimpleAgent:
    """
    Simple agent that executes tools based on user queries
    """

    def __init__(
        self,
        model_id: str = "",
        api_base: str = "",
        api_key: str = "",
        system_prompt: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        max_steps: int = 5,
        verbosity_level: int = 1
    ):
        """
        Initialize a SimpleAgent without any tools

        Args:
            model_id: Model ID to use (default: from env or openrouter/openai/gpt-4o-mini)
            api_base: API base URL (default: from env or OpenRouter)
            api_key: API key (default: from env)
            system_prompt: System prompt to use for the agent
            metadata: Metadata to pass to the LLM API
            max_steps: Maximum number of steps for the agent to take
            verbosity_level: Verbosity level (0-2)
        """
        # Set model parameters with defaults from environment variables
        self.model_id = model_id or os.getenv(
            "LITELLM_MODEL", "openrouter/openai/gpt-4o-mini"
        )
        self.api_base = api_base or os.getenv(
            "LITELLM_API_BASE", "https://openrouter.ai/api/v1"
        )
        self.api_key = api_key or os.getenv("LITELLM_API_KEY", "") or os.getenv(
            "OPENAI_API_KEY", ""
        )
        self.system_prompt = system_prompt
        self.metadata = metadata if metadata is not None else {}
        self.max_steps = max_steps
        self.verbosity_level = verbosity_level

        # Initialize tools and agent
        self.tools = []
        self.llm_agent = None

        # Add name and description attributes for Gradio UI
        self.name = "Simple Agent"
        self.description = "A lightweight AI agent that can execute various tools."

    def add_tools(self, tools: List[Callable]) -> None:
        """
        Add multiple tools to the agent

        Args:
            tools: List of tool functions decorated with @tool
        """
        for tool in tools:
            self.tools.append(tool)
        self._init_llm_agent()  # Reinitialize once after adding all tools

    def set_system_prompt(self, system_prompt: str) -> None:
        """
        Set the system prompt for the agent

        Args:
            system_prompt: The system prompt to use
        """
        self.system_prompt = system_prompt
        if self.llm_agent:
            # Reinitialize the agent with the new system prompt
            self._init_llm_agent()

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Set metadata to pass to the LLM API

        Args:
            metadata: Dictionary of metadata
        """
        self.metadata = metadata
        if self.llm_agent:
            # Reinitialize the agent with the new metadata
            self._init_llm_agent()

    def _init_llm_agent(self):
        """
        Initialize or reinitialize the LLM agent with current tools
        """
        try:
            # Create LiteLLM model with additional parameters
            model_kwargs = {}

            # Add API key if provided
            if self.api_key:
                model_kwargs["api_key"] = self.api_key

            # Add metadata if provided and convert to string format
            # that LiteLLM expects for metadata
            if self.metadata:
                model_kwargs["extra_body"] = {"metadata": self.metadata}

            # Create the LiteLLM model
            model = LiteLLMModel(
                model_id=self.model_id,
                api_base=self.api_base,
                **model_kwargs
            )

            # Create agent with tools and model
            agent_kwargs = {
                "tools": self.tools,
                "model": model,
                "max_steps": self.max_steps,
                "verbosity_level": self.verbosity_level
            }

            # Create the agent
            # Note: smolagents.ToolCallingAgent doesn't support system_prompt directly
            # We'll need to set it through the model's initialization if needed
            self.llm_agent = ToolCallingAgent(**agent_kwargs)

            # If system prompt is provided, try to set it on the agent
            # This is a workaround and may not work with all agent implementations
            if self.system_prompt and hasattr(self.llm_agent, "system_prompt"):
                self.llm_agent.system_prompt = self.system_prompt

            logger.info(f"Agent initialized with {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Error initializing LLM agent: {e}")
            self.llm_agent = None

    def run(self, query: str) -> str:
        """
        Run a query using the LLM agent

        Args:
            query: User query in natural language

        Returns:
            The agent's response
        """
        if not self.llm_agent:
            if len(self.tools) == 0:
                return "Error: No tools added to agent. Add tools first."
            else:
                self._init_llm_agent()  # Try to initialize again

            if not self.llm_agent:
                return "Error: Failed to initialize LLM agent."

        try:
            # Process the query with ToolCallingAgent
            response = self.llm_agent(query)
            return response
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error: {str(e)}"

    def launch_gradio_ui(
        self,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        share: bool = False,
        inbrowser: bool = True,
        initial_message: str = ""
    ):
        """
        Launch a Gradio UI for interacting with the agent

        Args:
            server_name: Server hostname
            server_port: Server port
            share: Whether to create a public link
            inbrowser: Whether to open in browser
            initial_message: Initial message to display
        """
        if not self.llm_agent:
            if len(self.tools) == 0:
                print("Error: No tools added to agent. Add tools first.")
                return
            else:
                self._init_llm_agent()  # Try to initialize again

            if not self.llm_agent:
                print("Error: Failed to initialize LLM agent.")
                return

        try:
            print(f"Launching Gradio UI with {len(self.tools)} tools")

            # Use our custom GradioUI class that handles None values
            ui = GradioUI(self.llm_agent)

            # Launch the UI
            ui.launch(
                server_name=server_name,
                server_port=server_port,
                share=share,
                inbrowser=inbrowser
            )

            # If initial message is provided, we would need to handle it
            if initial_message:
                print(f"Initial message: {initial_message}")
                print("Note: To display this in Gradio, modify the UI.")

        except Exception as e:
            logger.error(f"Error launching Gradio UI: {e}")
            print(f"Failed to launch UI: {e}")
