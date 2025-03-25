from pydantic2.agents.progress_form import BaseProgressForm, FormState
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time

load_dotenv()


class StartupForm(BaseModel):
    """Structure for storing startup form data"""
    idea_desc: str = Field(default="", description="Description of startup idea")
    target_mkt: str = Field(default="", description="Target market info")
    biz_model: str = Field(default="", description="Business model info")
    team_info: str = Field(default="", description="Team background")


class StartupFormResponse(BaseModel):
    """Response format for startup form analysis"""
    feedback: str = Field(description="Detailed feedback on the startup idea")
    score: float = Field(ge=0, le=10, description="Overall score of the startup idea")
    strengths: List[str] = Field(description="Key strengths of the startup idea")
    weaknesses: List[str] = Field(description="Areas for improvement")
    next_steps: List[str] = Field(description="Recommended next steps")
    market_potential: Optional[float] = Field(
        ge=0, le=10,
        description="Market potential score"
    )


class StartupFormProcessor(BaseProgressForm):
    """Processor for startup form data"""

    def __init__(self, user_id: str, session_id: str = None, verbose: bool = True):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm,
            form_prompt="""
            You are a naive startup founder who is asking for help to make a startup.
            Talk like a stupid.
            """,
            verbose=verbose,
            verbose_clients=False,
            session_id=session_id,
        )

        # Register tools
        self.tools = [self.analyze_startup]

        # Configure test agent
        self.configure_test_agent(
            prompt="""
            You are a naive startup founder who is asking for help to make a startup.
            Talk like a stupid.
            """,
            client=self._get_test_agent_client(temperature=0.7)
        )

    def analyze_startup(self, message: str) -> StartupFormResponse:
        """Analyze complete startup info when form is complete"""
        client = self._get_tool_client(temperature=0.7)

        client.message_handler.add_message_system(
            """
            You are a startup analyst. Generate a comprehensive analysis:
            1. Evaluate overall viability (0-10)
            2. List 3-5 key strengths
            3. List 2-3 areas for improvement
            4. Suggest 2-3 specific next steps
            5. Score market potential (0-10)
            """
        )

        client.message_handler.add_message_block(
            "STARTUP_INFO",
            self.current_state.form.model_dump()
        )

        try:
            result: StartupFormResponse = client.generate(
                result_type=StartupFormResponse
            )

            print("\n")
            print("="*50)
            print("🎉 STARTUP ANALYSIS SUCCESS 🎉")
            print("="*50)
            print(result.model_dump_json(indent=2))
            print("="*50)

            return result
        except Exception as e:
            raise Exception(f"Error analyzing startup: {str(e)}")

    def run_simple_dialog(self, messages: List[str]) -> str:
        """Run a simple dialog with automatic session creation

        This method simulates a new conversation where session is created automatically.

        Args:
            messages: List of user messages to process

        Returns:
            str: The session ID that was created
        """
        print("\n=== Simple Dialog Example (New Session) ===")

        # Process each message
        for i, message in enumerate(messages):
            print(f"\nQ{i+1}: {self.current_state.next_question}")
            print(f"A{i+1}: {message}")

            # Process the message
            result = self.process_form(message)
            print(f"Progress: {result.progress}%")

            # Show updated form data
            updated_form = result.form.model_dump()
            print("\nUpdated form data:")
            for key, value in updated_form.items():
                print(f"  {key}: {value or '[empty yet]'}")

            # Check if complete
            if result.progress >= 100:
                print("\n=== Form Complete, Running Analysis ===")
                analysis = self.analyze_startup(message)
                print(f"Score: {analysis.score}/10")
                break

            # Add a small delay to prevent rate limiting
            time.sleep(1)

        # Show final state
        print("\n=== Dialog Complete ===")
        print(f"Final Progress: {self.current_state.progress}%")
        print(f"Session ID: {self.db_manager.session_id}")

        return self.db_manager.session_id

    def continue_session_dialog(self, session_id: str, messages: List[str]) -> None:
        """Continue a dialog with an existing session

        This method simulates continuing a conversation with a known session ID.

        Args:
            session_id: The session ID to continue
            messages: List of user messages to process
        """
        print(f"\n=== Continue Session Dialog (ID: {session_id}) ===")

        # Set the session
        self.db_manager.set_session(session_id)

        # Show current state
        state_data = self.db_manager.restore_session_state(self.form_class)
        if state_data:
            print("\nCurrent form data:")
            for key, value in state_data['form'].model_dump().items():
                if value:
                    print(f"  {key}: {value}")

            print(f"\nCurrent question: {state_data['next_question']}")

        # Process each message
        for i, message in enumerate(messages):
            print(f"\nQ{i+1}: {self.current_state.next_question}")
            print(f"A{i+1}: {message}")

            # Process the message
            result = self.process_form(message)
            print(f"Progress: {result.progress}%")

            # Show updated form data
            updated_form = result.form.model_dump()
            print("\nUpdated form data:")
            for key, value in updated_form.items():
                if value:
                    print(f"  {key}: {value}")

            # Check if complete
            if result.progress >= 100:
                print("\n=== Form Complete, Running Analysis ===")
                analysis = self.analyze_startup(message)
                print(f"Score: {analysis.score}/10")
                break

            # Add a small delay to prevent rate limiting
            time.sleep(1)

        # Show final state
        print("\n=== Dialog Complete ===")
        print(f"Final Progress: {self.current_state.progress}%")
        print(f"Session ID: {self.db_manager.session_id}")

    def show_session_history(self, session_id: str = None) -> None:
        """Show the history of messages for a session

        Args:
            session_id: Optional session ID. If None, uses current session
        """
        if session_id:
            self.db_manager.set_session(session_id)

        print(f"\n=== Session History (ID: {self.db_manager.session_id}) ===")
        messages = self.db_manager.get_session_messages()

        if not messages:
            print("No messages found for this session")
            return

        print(f"Total messages: {len(messages)}")
        for i, message in enumerate(messages, 1):
            print(f"\nMessage {i}:")
            print(f"  Role: {message['role']}")
            print(f"  Content: {message['content']}")
            print(f"  Timestamp: {message['timestamp']}")

        # Show current form state
        state_data = self.db_manager.restore_session_state(self.form_class)
        if state_data:
            print("\nCurrent form state:")
            print(f"  Progress: {state_data['progress']}%")
            print(f"  Previous question: {state_data['prev_question']}")
            print(f"  Previous answer: {state_data['prev_answer']}")
            print(f"  Next question: {state_data['next_question']}")
            print("\nForm data:")
            for key, value in state_data['form'].model_dump().items():
                print(f"  {key}: {value or '[empty yet]'}")

    def process_form(self, message: str) -> FormState:
        """Process a message and update form state"""
        # Save user's message
        self.db_manager.save_chat_message('user', message)

        # Process with test agent
        result = super().process_form(message)

        # Save assistant's response
        self.db_manager.save_chat_message('assistant', result.next_question)

        return result


def main(session_id: str = None):
    """Example usage of StartupFormProcessor"""
    user_id = "test_user"

    # Create processor instance
    processor = StartupFormProcessor(
        user_id=user_id,
        session_id=session_id,
        verbose=True
    )

    # Example messages for new session
    new_session_messages = [
        "I'm building a food delivery app for local restaurants",
        "Target market is urban professionals who value local cuisine",
        "Revenue from 10% restaurant commission and small delivery fee"
    ]

    # Example messages for continuing session
    continue_messages = [
        "We have a team of 5 experienced developers",
        "Our main competitor is Uber Eats"
    ]

    # # Example 1: Run simple dialog (new session)
    # print("\n--- Example 1: New Session Dialog ---")
    # new_session_id = processor.run_simple_dialog(new_session_messages)

    # Show history for new session
    new_session_id = "307e77d3-6d51-4eac-8332-d1f4071b8752"
    processor.show_session_history(new_session_id)

    # # Example 2: Continue existing session
    # print("\n--- Example 2: Continue Existing Session ---")
    # processor.continue_session_dialog(new_session_id, continue_messages)

    # # Show updated history
    # processor.show_session_history(new_session_id)


if __name__ == "__main__":
    # Example session ID for testing
    test_session_id = "8c73deed-e676-4379-b11f-5c066a3b3ff2"
    main(test_session_id)
