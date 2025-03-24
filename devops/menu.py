#!/usr/bin/env python3
import subprocess
from pathlib import Path
from typing import Optional
import re
import questionary
import semver
import toml


class DeployManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.package_name = self._get_package_name()
        self.current_version = self._get_current_version()
        self.style = questionary.Style(
            [
                ("question", "fg:cyan bold"),
                ("answer", "fg:yellow"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
                ("selected", "fg:green bold"),
                ("separator", "fg:blue"),
                ("instruction", "fg:white italic"),
                ("input", "fg:white"),
                ("error", "fg:red bold"),
            ]
        )

        # Defining command groups
        self.commands = {
            "Development": {
                'Check security': self.check_security,
                "Check Environment": self.check_environment,
                "Install Package": self.install_package,
                "Run Tests": self.run_tests,
                "Format Code": self.format_code,
                "Check Linting": self.check_lint,
                "Print Tree": self.print_tree,
            },
            "Version Control": {
                "Update Version": self.update_version,
                "Show Changes": self.show_changes,
            },
            "Package Management": {
                "Build Package": self.build_package,
                f"Upload to TestPyPI (v{self.current_version})":
                    self.upload_to_testpypi,
                f"Upload to PyPI (v{self.current_version})":
                    self.upload_to_pypi,
                "Clean Builds": self.clean_builds,
            },
        }

    def _get_package_name(self) -> str:
        """Get package name from pyproject.toml."""
        pyproject_toml = self.root_dir / "pyproject.toml"

        try:
            data = toml.load(pyproject_toml)
            package_name = data["tool"]["poetry"]["name"]
            if not package_name:
                raise ValueError("Package name not found in pyproject.toml")

            return package_name
        except Exception as e:
            raise ValueError(f"Error reading package name from pyproject.toml: {e}")

    def run_command(
        self, command: str, description: str = "", check: bool = True
    ) -> bool:
        """Run a shell command and handle errors."""
        print(f"\n📋 {description or command}")
        try:
            result = subprocess.run(
                command, shell=True, check=check, text=True, capture_output=True
            )
            if result.stdout:
                print(f"📤 Output:\n{result.stdout}")
            if result.returncode == 0:
                print(f"✅ Success: {description or command}")
                return True
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            print(f"📥 Error output:\n{e.stderr}")
            return False

    def print_tree(self) -> bool:
        """Print tree of files in current directory."""
        return self.run_command(
            "git ls-files --others --exclude-standard --cached | tree --fromfile",
            "Printing tree of files"
        )

    def check_environment(self) -> bool:
        """Check development environment."""
        commands = [
            ("poetry --version", "Poetry version"),
            ("poetry show", "Installed packages"),
            (
                "tree -I 'venv|__pycache__|*.pyc|*.pyo|*.pyd|.git|"
                ".pytest_cache|*.egg-info|dist|build'",
                "Project structure",
            ),
        ]
        return all(self.run_command(cmd, desc) for cmd, desc in commands)

    def install_package(self) -> bool:
        """Install package using Poetry."""
        return self.run_command("poetry install", "Installing package")

    def run_tests(self) -> bool:
        """Run test suite."""
        return self.run_command(
            "poetry run pytest -v --cov=src/pydantic2 --cov-report=term-missing tests/",
            "Running tests with coverage"
        )

    def format_code(self) -> bool:
        """Format code using black and isort."""
        commands = [
            ("poetry run black .", "Formatting with black"),
            ("poetry run isort .", "Sorting imports"),
        ]
        return all(self.run_command(cmd, desc) for cmd, desc in commands)

    def check_lint(self) -> bool:
        """Run linting checks."""
        commands = [
            ("poetry run flake8 .", "Running flake8"),
            ("poetry run mypy .", "Running type checks")
        ]
        return all(self.run_command(cmd, desc) for cmd, desc in commands)

    def check_security(self) -> bool:
        """Run security audit on dependencies using multiple tools."""
        print("\n🔍 Running security checks...")

        # Create reports directory if it doesn't exist
        reports_dir = self.root_dir / "security_reports"
        reports_dir.mkdir(exist_ok=True)

        # Generate timestamp for report files
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Run pip-audit for Python-specific vulnerabilities
        print("\n📦 Checking with pip-audit:")
        pip_audit_report = reports_dir / f"pip_audit_{timestamp}.json"
        pip_audit_cmd = f"poetry run pip-audit --local --format json -o {pip_audit_report}"
        has_pip_audit_issues = not self.run_command(pip_audit_cmd, "Running pip-audit check")

        # If pip-audit found issues, offer to fix them
        if has_pip_audit_issues:
            if questionary.confirm(
                "Would you like pip-audit to attempt fixing the vulnerabilities?"
            ).ask():
                fix_cmd = "poetry run pip-audit --fix"
                self.run_command(fix_cmd, "Attempting to fix vulnerabilities", check=False)

        # Run safety scan with basic output
        print("\n🔒 Checking with Safety CLI:")
        safety_report = reports_dir / f"safety_{timestamp}.txt"
        safety_cmd = f"poetry run safety scan --short-report | tee {safety_report}"
        result = subprocess.run(safety_cmd, shell=True, text=True, capture_output=True)

        # Check if Safety CLI requires login
        if "Please login or register Safety CLI" in result.stdout or \
           "Please login or register Safety CLI" in result.stderr:
            print("\n⚠️  Safety CLI requires authentication")
            print("📝 To use Safety CLI, you need to:")
            print("1. Register for a free account at https://safetycli.com")
            print("2. Login using 'safety auth login'")
            print("3. Run the security check again")

            # Save the login prompt for reference
            with open(safety_report, 'w') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\nError output:\n")
                    f.write(result.stderr)

            print(f"\n📋 Login prompt saved to: {safety_report}")
            has_safety_issues = True
        else:
            has_safety_issues = result.returncode != 0
            if result.stdout:
                print(f"📤 Output:\n{result.stdout}")
            if result.stderr:
                print(f"📥 Error output:\n{result.stderr}")

        # If issues found and we're authenticated, offer quick fixes
        if has_safety_issues and "Please login or register Safety CLI" not in result.stdout:
            if questionary.confirm("Would you like to attempt automatic fixes?").ask():
                fix_level = questionary.select(
                    "Select maximum version update level for automatic fixes:",
                    choices=["patch", "minor", "major"],
                    default="patch"
                ).ask()

                if fix_level:
                    # Use no-prompt for faster execution
                    safety_fix_cmd = (
                        f"poetry run safety scan --apply-security-updates "
                        f"--auto-security-updates-limit {fix_level} --no-prompt"
                    )
                    self.run_command(safety_fix_cmd, "Applying security fixes", check=False)

        print("\nSecurity check completed. Please review any findings above.")
        if has_pip_audit_issues or has_safety_issues:
            print("⚠️  Security issues were found in your dependencies.")
            print("📝 Note: Some findings might be false positives")
            print("💡 Tips:")
            print("  - Use 'poetry update' to update dependencies")
            print("  - Review 'poetry.lock' for any known vulnerable dependencies")
            print(f"  - Security reports saved to {reports_dir}")
            print("  - For detailed reports, run 'safety scan --full-report'")
        else:
            print("✅ No known vulnerabilities found.")
            print(f"📝 Clean security reports saved to {reports_dir}")

        return True

    def show_changes(self) -> bool:
        """Show current git changes."""
        commands = [
            ("git status", "Current git status"),
            ("git diff", "Current changes"),
        ]
        return all(self.run_command(cmd, desc) for cmd, desc in commands)

    def clean_builds(self) -> bool:
        """Clean all build artifacts."""
        return self.run_command(
            "rm -rf dist build *.egg-info __pycache__ .pytest_cache .mypy_cache",
            "Cleaning build artifacts"
        )

    def build_package(self) -> bool:
        """Build package distributions."""
        if not self.clean_builds():
            return False

        return self.run_command("poetry build", "Building package")

    def upload_to_testpypi(self) -> bool:
        """Upload package to TestPyPI."""
        if not questionary.confirm(
            "Are you sure you want to upload to TestPyPI?"
        ).ask():
            return False

        print("\n🧪 Running tests before uploading to TestPyPI...")
        if not self.run_tests():
            print("❌ Tests failed! Aborting upload to TestPyPI.")
            return False

        print("\n🔒 Running security audit...")

        if questionary.confirm("Do you want to run the security audit?").ask():
            if not self.check_security():
                print("❌ Security audit failed! Please review the vulnerabilities above.")
                if not questionary.confirm("Continue despite security warnings?").ask():
                    return False

        print("\n🔨 Tests passed! Building package...")
        if not self.build_package():
            print("❌ Package build failed! Aborting upload to TestPyPI.")
            return False

        return self.run_command(
            "poetry publish -r testpypi", "Uploading to TestPyPI"
        )

    def upload_to_pypi(self) -> bool:
        """Upload package to PyPI."""
        if not questionary.confirm("Are you sure you want to upload to PyPI?").ask():
            return False

        print("\n🧪 Running tests before uploading to PyPI...")
        if not self.run_tests():
            print("❌ Tests failed! Aborting upload to PyPI.")
            return False

        print("\n🔒 Running security audit...")
        if questionary.confirm("Do you want to run the security audit?").ask():
            if not self.check_security():
                print("❌ Security audit failed! Please review the vulnerabilities above.")
                if not questionary.confirm("Continue despite security warnings?").ask():
                    return False

        print("\n🔨 Tests passed! Building package...")
        if not self.build_package():
            print("❌ Package build failed! Aborting upload to PyPI.")
            return False

        return self.run_command("poetry publish", "Uploading to PyPI")

    def update_version(self) -> bool:
        """Update package version."""
        current_version = self._get_current_version()
        if not current_version:
            return False

        try:
            # Parse current version
            ver = semver.Version.parse(current_version)
            print(f"\n📦 Current version: {current_version}")

            # Always show version type selection
            increment_type = questionary.select(
                "Select version increment type:",
                choices=["patch", "minor", "major"],
                default="patch"
            ).ask()

            # If it's a prerelease version, increment the prerelease number
            if ver.prerelease:
                prefix = str(ver.prerelease).split('.')[0]
                number = int(str(ver.prerelease).split('.')[1])
                new_version = (
                    f"{ver.major}.{ver.minor}.{ver.patch}-{prefix}.{number + 1}"
                )
            else:
                # For stable versions, increment version number
                if increment_type == "patch":
                    ver = ver.bump_patch()
                elif increment_type == "minor":
                    ver = ver.bump_minor()
                elif increment_type == "major":
                    ver = ver.bump_major()
                new_version = str(ver)

            self._update_version_in_files(new_version)
            print(f"✅ Version updated: {current_version} → {new_version}")
            return True

        except ValueError as e:
            print(f"❌ Error parsing version: {e}")
            return False

    def _get_current_version(self) -> Optional[str]:
        """Get current package version from pyproject.toml."""
        pyproject_toml = self.root_dir / "pyproject.toml"
        if not pyproject_toml.exists():
            print("❌ pyproject.toml not found")
            return None

        try:
            data = toml.load(pyproject_toml)
            version = data["tool"]["poetry"]["version"]
            if not version:
                print("❌ Version not found in pyproject.toml")
                return None

            return version
        except Exception as e:
            print(f"❌ Error reading pyproject.toml: {e}")
            return None

    def _update_version_in_files(self, new_version: str) -> None:
        """Update version in configuration files."""
        module_name = self.package_name
        pyproject_toml = self.root_dir / "pyproject.toml"

        # Update pyproject.toml
        if pyproject_toml.exists():
            try:
                data = toml.load(pyproject_toml)
                data["tool"]["poetry"]["version"] = new_version

                with open(pyproject_toml, "w") as f:
                    toml.dump(data, f)
            except Exception as e:
                print(f"❌ Error updating pyproject.toml: {e}")

        # Update version in __pack__.py if it exists
        init_path = self.root_dir / "src" / module_name / "__pack__.py"

        # update __pack__.py
        if init_path.exists():
            with open(init_path) as f:
                content = f.read()

            # update __version__
            content = re.sub(
                r'__version__ = ".*"',
                f'__version__ = "{new_version}"',
                content
            )

            # update __name__
            content = re.sub(
                r'__name__ = ".*"',
                f'__name__ = "{module_name}"',
                content
            )

            with open(init_path, "w") as f:
                f.write(content)

    def show_menu(self) -> None:
        """Display interactive menu."""
        while True:
            choices = []
            for group, commands in self.commands.items():
                if choices:
                    choices.append(questionary.Separator())
                choices.append(questionary.Separator(f"━━ {group} ━━"))
                choices.extend(list(commands.keys()))

            choices.extend([questionary.Separator("━" * 30), "Exit"])

            action = questionary.select(
                message=f"{self.package_name.upper()} v{self.current_version}",
                choices=choices,
                style=self.style,
            ).ask()

            if not action or action == "Exit":
                break

            for commands in self.commands.values():
                if action in commands:
                    try:
                        commands[action]()
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        if not questionary.confirm("Continue?", style=self.style).ask():
                            return
                    break


if __name__ == "__main__":
    manager = DeployManager()
    manager.show_menu()
