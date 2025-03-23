from typing import Any
import yaml
import re
from bs4 import BeautifulSoup
import json
from pydantic import BaseModel
from ..utils.logger import logger


class MessageFormatError(Exception):
    """Raised when message format is not suitable for conversion."""
    pass


class MessageHandler:
    # Allowed types for messages
    ALLOWED_TYPES = (str, int, float, bool, dict, list)

    def __init__(self):
        self.messages = []

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []

    def _add_message(self, role: str, content: Any, to_flat_yaml: bool = True) -> None:
        """Add a message to the list."""
        if to_flat_yaml:
            content = self.to_flat_yaml(content)

        if not self._validate_message(role, content):
            logger.error(f"Message already exists: {content}")
            return

        self.messages.append({"role": role, "content": content})

    def _validate_message(self, role: str, content: Any) -> bool:
        """Validate if message is already in the list."""
        for message in self.messages:
            if message["role"] == role and message["content"] == content:
                return False
        return True

    def add_message_system(self, content: Any):
        """Add a system message."""
        # formatted_content = self.to_flat_yaml(content)
        self._add_message("system", content)

    def add_message_user(self, content: Any):
        """Add a user message."""
        self._add_message("user", content)

    def add_message_assistant(self, content: Any):
        """Add an assistant message."""
        self._add_message("assistant", content)

    def add_message_block(self, block_type: str, content: Any):
        """Add a structured data block."""
        block_type = block_type.upper()
        self._add_message("user", f"[{block_type}]:\n{content}\n[/{block_type}]", to_flat_yaml=False)

    def format_raw_request(self) -> str:
        """Format the complete request for logging."""
        formatted = []
        for message in self.messages:
            formatted.append(f"{message['role']}:\n{message['content']}\n")
        return "\n\n".join(formatted)

    def get_formatted_prompt(self) -> str:
        """Get a formatted string representation of all messages."""
        formatted = []

        for message in self.messages:
            formatted.append(f"{message['role']}:\n{message['content']}\n")

        return "\n\n".join(formatted)

    def add_model_schema(self, answer_model: type[BaseModel]):
        """Generate schema instructions for the model."""
        schema = answer_model.model_json_schema()
        # Remove metadata that might confuse the AI
        schema.pop('title', None)
        schema.pop('type', None)

        response = f"""
        Response:
        - Return only ONE clean JSON object based on the schema.
        - No code blocks, no extra text, just the JSON object.
        - Make sure the JSON is valid and properly formatted.
        - Do not return the schema itself, return only the JSON object based on
          the schema.
        [SCHEMA]
        {json.dumps(schema)}
        [/SCHEMA]

        """
        result = self.trim_message(response)
        self.messages.append({"role": "system", "content": result})

    @staticmethod
    def trim_message(message: str) -> str:
        """Trim all types of whitespace from the message using regex.

        Args:
            message: Message to trim

        Returns:
            Message with trimmed whitespace
        """
        # Remove leading/trailing whitespace from each line
        # and collapse multiple spaces into single space
        lines = message.split('\n')
        trimmed_lines = [
            re.sub(r'\s+', ' ', line.strip())
            for line in lines
        ]
        # Remove empty lines at start and end
        while trimmed_lines and not trimmed_lines[0]:
            trimmed_lines.pop(0)
        while trimmed_lines and not trimmed_lines[-1]:
            trimmed_lines.pop()
        return '\n'.join(trimmed_lines)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Clean text from special characters and HTML tags"""
        # Remove HTML tags
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        # Normalize whitespace
        return ' '.join(text.split()).strip()

    @staticmethod
    def to_flat_yaml(data: Any, section: str | None = None) -> str:
        """Convert nested data to flat YAML format with optional section header"""

        """Validate if message type is supported."""
        if not isinstance(data, MessageHandler.ALLOWED_TYPES):
            type_name = type(data).__name__
            allowed_types = ', '.join(t.__name__ for t in MessageHandler.ALLOWED_TYPES)
            raise MessageFormatError(
                f"Unsupported message type: {type_name}. "
                f"Allowed types are: {allowed_types}"
            )

        # First convert to YAML with proper indentation
        yaml_str = yaml.dump(
            data,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
            width=200,
            explicit_start=False,
            explicit_end=False,
            canonical=False,
            default_style='',
        )

        # Add section markers if section is provided
        if section:
            section = section.upper()
            return f"[{section}]:\n{yaml_str}\n[/{section}]"

        return yaml_str
