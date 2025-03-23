from pydantic2.agents.progress_form import BaseProgressForm
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

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

    def __init__(self, user_id: str, session_id: str = None):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm,
            form_prompt="""
            Ask in Russian.
            """,
            verbose=True,
            verbose_clients=False,
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

        # Set session if provided
        if session_id:
            self._set_session(session_id)

    def analyze_startup(
        self,
        message: str,
        session_id: str = None
    ) -> StartupFormResponse:
        """Analyze complete startup info when form is complete"""
        if session_id and session_id != self.db_manager.session_id:
            self._set_session(session_id)

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

    def start_session_dialog(self, messages: List[str]) -> None:
        """Run a simple dialog without explicit session handling

        Args:
            messages: List of user messages to process
        """
        print("\n=== Simple Dialog Example ===")

        # Set initial question if needed
        if not self.current_state.next_question:
            self.current_state.next_question = "Tell me about your startup idea."
            self.save_current_state()

        # Process each message
        for i, message in enumerate(messages):
            print(f"\nQ{i+1}: {self.current_state.next_question}")
            print(f"A{i+1}: {message}")

            # Process the message
            result = self.process_form(message)
            print(f"Progress: {result.progress}%")

            # Check if complete
            if result.progress >= 100:
                print("\n=== Form Complete, Running Analysis ===")
                analysis = self.analyze_startup(message)
                print(f"Score: {analysis.score}/10")
                break

        print("=== Simple Dialog Complete ===\n")

    def continue_session_dialog(self, session_id: str) -> str:
        """Run a dialog with explicit session handling

        Args:
            session_id: Optional session ID to use. If None, creates a new session.

        Returns:
            The session ID used for the dialog

        Raises:
            ValueError: If provided session_id is invalid or not found
        """
        try:
            # Get or create session
            self._set_session(session_id)
            print(f"\n=== Session Dialog Example (ID: {session_id}) ===")

            # Always refresh state to get the latest data
            self.refresh_current_state()

            # Show current state of the form
            current_form = self.current_state.form.model_dump()
            print("Current form data:")
            for key, value in current_form.items():
                if value:
                    print(f"  {key}: {value}")

            # Get current question from refreshed state
            current_question = self.current_state.next_question
            if not current_question:
                current_question = "Tell me about your startup idea."
                self.current_state.next_question = current_question
                self.save_current_state()

            print(f"\nCurrent question: {current_question}")

            # Example messages
            messages = [
                # 'Пиццы из воска для богатых'
                "Гномы будут делать"
            ]

            # Process each message
            for i, message in enumerate(messages):
                print(f"User answer: {message}")

                # Show message being processed
                print("\n--- Processing message ---")

                # Process the message using the current session
                result = self.process_form(message)
                print(f"Progress: {result.progress}%")

                # Show the new question
                print(f"\nNew question: {result.next_question}")

                # Debug - show form state after processing
                updated_form = result.form.model_dump()
                print("\nUpdated form data:")
                for key, value in updated_form.items():
                    if value:
                        print(f"  {key}: {value}")

            print("\n=== Session Dialog Paused ===")
            print(f"Session ID: {session_id} (can be used to continue later)\n")

            return session_id

        except Exception as e:
            print(f"Error in session dialog: {e}")
            raise


def main():
    """Example usage of StartupFormProcessor with dialog examples"""
    user_id = "test_user"

    # Create a new processor instance
    print("\n--- Creating processor instance ---")
    new_processor = StartupFormProcessor(user_id=user_id)

    # Use existing session or create a new one
    session_id = '2e1b42b1-6c8a-48f6-9cb9-292bad716d16'

    # Show session history
    print("\n--- Session History ---")
    try:
        history = new_processor.get_session_history(session_id)
        print(f"Total states in session: {len(history)}")

        if history:
            latest_state = history[-1]
            print(f"Latest progress: {latest_state.get('progress')}%")
            print(f"Latest question: {latest_state.get('next_question')}")
    except ValueError:
        print(f"Session {session_id} not found, will create new session")
        session_id = new_processor.get_session_id()

    # Continue the conversation with the session
    print("\n--- Continue dialog with session ---")
    new_processor.continue_session_dialog(session_id)

    # Show the updated session history
    print("\n--- Updated Session History ---")
    history = new_processor.get_session_history(session_id)
    print(f"Total states in session: {len(history)}")

    if history:
        latest_state = history[-1]
        print(f"Latest progress: {latest_state.get('progress')}%")
        print(f"Latest question: {latest_state.get('next_question')}")


if __name__ == "__main__":
    main()
