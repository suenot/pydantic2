"""
Debug utilities for development and testing.
"""
import os
import logging
from typing import List, Dict, Any
import importlib.util
import questionary


class DebugTools:
    """
    A class for navigating and running example files.
    """

    def __init__(self):
        """Initialize debug tools."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Configure console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def get_example_files(self) -> Dict[str, Any]:
        """
        Get tree structure of example files.

        Returns:
            Dictionary representing the file tree
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        examples_dir = os.path.join(project_root, 'src', 'examples')

        def build_tree(path: str) -> Dict[str, Any]:
            tree = {}
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    tree[item] = build_tree(full_path)
                elif item.endswith('.py'):
                    tree[item] = full_path
            return tree

        return build_tree(examples_dir)

    def create_choices(self, tree: Dict[str, Any], prefix: str = "", level: int = 0) -> List[questionary.Choice]:
        """
        Create questionary choices from tree structure.

        Args:
            tree: File tree dictionary
            prefix: Path prefix for nested items
            level: Current nesting level

        Returns:
            List of questionary choices
        """
        choices = []
        indent = "  " * level
        is_last = True

        # Sort items to show directories first, then files
        items = sorted(tree.items(), key=lambda x: (not isinstance(x[1], dict), x[0]))

        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "

            if isinstance(value, dict):
                # Directory
                choices.append(questionary.Choice(
                    title=f"{indent}{connector}📁 {name}/",
                    value=f"dir:{prefix}{name}",
                    description=f"Browse directory: {name}"
                ))
                choices.extend(self.create_choices(value, f"{prefix}{name}/", level + 1))
            else:
                # File
                choices.append(questionary.Choice(
                    title=f"{indent}{connector}📄 {name}",
                    value=f"file:{value}",
                    description=f"Run example: {name}"
                ))

        # Add back option for nested directories
        if prefix:
            choices.append(questionary.Choice(
                title=f"{indent}└── 🔙 ..",
                value="back",
                description="Go back"
            ))

        return choices

    def run_example_file(self, file_path: str) -> None:
        """
        Run an example file.

        Args:
            file_path: Path to the example file
        """
        self.logger.info(f"\nRunning example: {os.path.basename(file_path)}")
        self.logger.info("=" * 80)

        try:
            spec = importlib.util.spec_from_file_location("example_module", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, 'main'):
                    module.main()
        except Exception as e:
            self.logger.error(f"Error running example: {str(e)}")

    def show_menu(self) -> None:
        """Show interactive menu for browsing and running examples."""
        current_path = []

        while True:
            # Get current tree level
            tree = self.get_example_files()
            for path in current_path:
                tree = tree[path]

            # Create choices for current level
            choices = self.create_choices(tree, "/".join(current_path) + "/" if current_path else "")

            # Add exit option
            choices.append(questionary.Choice(
                title="❌ Exit",
                value="exit",
                description="Exit debug menu"
            ))

            # Show current path
            current_location = "📂 examples/" + "/".join(current_path) if current_path else "📂 examples"
            self.logger.info(f"\n{current_location}")
            self.logger.info("=" * 80)

            # Show menu
            answer = questionary.select(
                "Select an example to run:",
                choices=choices
            ).ask()

            if answer == "exit":
                break
            elif answer == "back":
                current_path.pop()
                continue
            elif answer.startswith("dir:"):
                # Navigate into directory
                dir_name = answer[4:].rstrip("/")
                current_path.append(dir_name)
                continue
            elif answer.startswith("file:"):
                # Run example file
                file_path = answer[5:]
                self.run_example_file(file_path)
                input("\nPress Enter to continue...")


def main():
    """Main entry point for the debug menu."""
    debug = DebugTools()
    debug.show_menu()


if __name__ == "__main__":
    main()
