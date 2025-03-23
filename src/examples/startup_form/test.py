from pydantic2.agents.progress_form import BaseProgressForm
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time
import concurrent.futures

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
            Ask in Russian.
            """,
            verbose=verbose,
            verbose_clients=False,
            default_session_id=session_id,  # Use the default session ID parameter
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

    def analyze_startup(
        self,
        message: str,
        session_id: str = None
    ) -> StartupFormResponse:
        """Analyze complete startup info when form is complete"""
        # Use temporary session context manager if needed
        if session_id and session_id != self.db_manager.session_id:
            with self.temporary_session(session_id):
                return self._do_analyze_startup(message)
        else:
            return self._do_analyze_startup(message)

    def _do_analyze_startup(self, message: str) -> StartupFormResponse:
        """Internal implementation of startup analysis"""
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

    def run_simple_dialog(self, messages: List[str]) -> None:
        """Run a simple dialog without explicit session handling

        This optimized version uses process_form_batch to reduce database writes.

        Args:
            messages: List of user messages to process
        """
        print("\n=== Simple Dialog Example ===")

        # Set initial question if needed
        if not self.current_state.next_question:
            self.current_state.next_question = "Tell me about your startup idea."
            self.save_current_state()

        # Use batch processing for better performance
        if len(messages) > 1:
            start_time = time.time()
            # Process all but the last message in batch
            batch_msgs = messages[:len(messages)-1]
            results = self.process_form_batch(batch_msgs)

            # Display results for each processed message
            for i, (message, result) in enumerate(zip(batch_msgs, results)):
                print(f"\nQ{i+1}: {result.prev_question}")
                print(f"A{i+1}: {message}")
                print(f"Progress: {result.progress}%")
            end_time = time.time()
            print(f"Batch processing time: {end_time - start_time:.2f}s")

        # Process the last message individually
        if messages:
            last_message = messages[-1]
            print(f"\nQ{len(messages)}: {self.current_state.next_question}")
            print(f"A{len(messages)}: {last_message}")

            # Process the message
            result = self.process_form(last_message)
            print(f"Progress: {result.progress}%")

            # Check if complete
            if result.progress >= 100:
                print("\n=== Form Complete, Running Analysis ===")
                analysis = self.analyze_startup(last_message)
                print(f"Score: {analysis.score}/10")

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
            # Set the session using exception-safe method
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
                "My startup makes wax pizzas for rich people"
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

    def benchmark_concurrent_sessions(self, num_sessions: int = 3):
        """Benchmark processing multiple sessions concurrently

        Args:
            num_sessions: Number of sessions to create and process
        """
        print(f"\n=== Concurrent Sessions Benchmark ({num_sessions} sessions) ===")

        # Create session IDs
        session_ids = []
        for i in range(num_sessions):
            with self.temporary_session(None):
                session_id = self.get_session_id()
                session_ids.append(session_id)
                print(f"Created session {i+1}: {session_id}")

        # Define messages for processing
        messages = [
            "My startup creates AI-powered gardening tools",
            "We target home gardeners and small farms",
            "Revenue from hardware sales and subscription"
        ]

        # Function to process a single session
        def process_session(session_id):
            start_time = time.time()
            with self.temporary_session(session_id):
                # Set initial question
                if not self.current_state.next_question:
                    self.current_state.next_question = "Tell me about your startup idea."
                    self.save_current_state()

                # Process messages
                for msg in messages:
                    self.process_form(msg)

                # Get final state
                final_state = self.current_state.model_dump()
                duration = time.time() - start_time
                return session_id, final_state, duration

        # Process sessions using ThreadPoolExecutor
        start_total = time.time()
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
            future_to_session = {
                executor.submit(process_session, session_id): session_id
                for session_id in session_ids
            }

            for future in concurrent.futures.as_completed(future_to_session):
                session_id = future_to_session[future]
                try:
                    session_id, final_state, duration = future.result()
                    results.append((session_id, final_state, duration))
                except Exception as e:
                    print(f"Session {session_id} generated an exception: {e}")

        total_duration = time.time() - start_total

        # Print results
        print("\n=== Benchmark Results ===")
        print(f"Total processing time: {total_duration:.2f}s")
        for session_id, final_state, duration in results:
            print(f"Session {session_id}: {duration:.2f}s - "
                  f"Progress: {final_state['progress']}%")

        # Average processing time
        avg_time = sum(r[2] for r in results) / len(results)
        print(f"Average session processing time: {avg_time:.2f}s")
        speedup = (avg_time * num_sessions) / total_duration
        print(f"Concurrent speedup: {speedup:.2f}x")

        return session_ids


def main(session_id: str = None):
    """Example usage of StartupFormProcessor with dialog examples"""
    user_id = "test_user"

    # Create a new processor instance with verbose output
    print("\n--- Creating processor instance with verbose output ---")
    processor = StartupFormProcessor(user_id=user_id, verbose=True)

    # Get a new session ID
    if session_id is None:
        session_id = processor.get_session_id()
        print(f"Using session ID: {session_id}")

    # -----------------------------------------
    # Example 1: Simple dialog with batch processing (verbose)
    # -----------------------------------------
    print("\n--- Example 1: Simple Dialog with Batch Processing (verbose) ---")
    messages = [
        "I'm building a food delivery app for local restaurants",
        "Target market is urban professionals who value local cuisine",
        "Revenue from 10% restaurant commission and small delivery fee"
    ]
    processor.run_simple_dialog(messages)

    # -----------------------------------------
    # Example 2: Toggle verbose setting (now OFF)
    # -----------------------------------------
    print("\n--- Example 2: Toggle verbose setting OFF ---")
    processor.verbose = False
    processor.set_verbose()  # Update logging levels

    # Continue the dialog with verbose OFF
    print("\n--- Session dialog continuation with verbose OFF ---")
    processor.continue_session_dialog(session_id)

    # -----------------------------------------
    # Example 3: History Retrieval (verbose OFF)
    # -----------------------------------------
    print("\n--- Example 3: History Retrieval (OFF) ---")
    history = processor.get_session_history(session_id, limit=5)
    print(f"Total states in session: {len(history)}")
    if history:
        latest_state = history[-1]
        print(f"Latest progress: {latest_state.get('progress')}%")
        print(f"Latest question: {latest_state.get('next_question')}")

    # -----------------------------------------
    # Example 4: Toggle verbose setting (now ON again)
    # -----------------------------------------
    print("\n--- Example 4: Toggle verbose setting ON again ---")
    processor.verbose = True
    processor.set_verbose()  # Update logging levels

    # Get session history with verbose ON
    print("\n--- Session history with verbose ON ---")
    history = processor.get_session_history(session_id, limit=3)
    print(f"Retrieved {len(history)} most recent states")

    # -----------------------------------------
    # Example 5: Create non-verbose processor for comparison
    # -----------------------------------------
    print("\n--- Example 5: Non-verbose processor ---")
    quiet_processor = StartupFormProcessor(user_id=user_id, verbose=False)
    quiet_session_id = quiet_processor.get_session_id()
    print(f"Created quiet session: {quiet_session_id}")

    # Process a simple message with quiet processor
    quiet_processor.process_form("This is a quiet startup for introverts")
    print("Processed message with non-verbose processor")

    print("\n--- Done ---")


if __name__ == "__main__":
    test_session_id = "8c73deed-e676-4379-b11f-5c066a3b3ff2"
    main(test_session_id)
