from typing import Any
import yaml


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

    def _validate_message(self, message: Any) -> None:
        """Validate if message type is supported."""
        if not isinstance(message, self.ALLOWED_TYPES):
            type_name = type(message).__name__
            allowed_types = ', '.join(t.__name__ for t in self.ALLOWED_TYPES)
            raise MessageFormatError(
                f"Unsupported message type: {type_name}. "
                f"Allowed types are: {allowed_types}"
            )

    def _format_data(self, data: Any) -> str:
        """Format data in a readable way using YAML."""
        self._validate_message(data)

        if isinstance(data, (dict, list)):
            yaml_str = yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2
            )
            return yaml_str.strip()
        else:
            return str(data)

    def add_message_system(self, content: str):
        """Add a system message."""
        self.messages.append({"role": "system", "content": content})

    def add_message_user(self, content: str):
        """Add a user message."""
        self.messages.append({"role": "user", "content": content})

    def add_message_assistant(self, content: str):
        """Add an assistant message."""
        self.messages.append({"role": "assistant", "content": content})

    def add_message_block(self, block_type: str, content: dict):
        """Add a structured data block."""
        formatted_content = f"{block_type}:\n" + "\n".join(f"{k}: {v}" for k, v in content.items())
        self.messages.append({"role": "system", "content": formatted_content})

    def get_messages(self):
        """Get all messages."""
        return self.messages

    def get_system_prompt(self) -> str:
        """Get combined system prompt."""
        system_messages = [msg["content"] for msg in self.messages if msg["role"] == "system"]
        return "\n".join(system_messages)

    def get_user_prompt(self) -> str:
        """Get combined user and assistant messages."""
        user_messages = [msg["content"] for msg in self.messages if msg["role"] in ("user", "assistant")]
        return "\n".join(user_messages)

    def format_raw_request(self) -> str:
        """Format the complete request for logging."""
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt()
        return "\n".join(filter(None, [system_prompt, user_prompt]))

    def get_formatted_prompt(self) -> str:
        """Get a formatted string representation of all messages."""
        formatted = []

        for message in self.messages:
            formatted.append(f"{message['role']}:\n{message['content']}\n")

        return "\n\n".join(formatted)
