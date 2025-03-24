import subprocess
import os
from pathlib import Path
import click
import socket
import signal
import sys
import time
import colorlog
import logging
import psutil
import questionary
import webbrowser
from typing import Optional, List, Tuple, Dict

# Configure colored logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s %(reset)s %(message)s',
    datefmt='%H:%M:%S',
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }
))

logger = logging.getLogger('datasette_viewer')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

DB_DIR = Path(__file__).parent.parent / "db"
MODELS_DB = DB_DIR / "models.db"
USAGE_DB = DB_DIR / "usage.db"
SESSIONS_DB = DB_DIR / "sessions.db"

# Global list to track running processes
running_processes: List[subprocess.Popen] = []

# Database configurations
DB_CONFIGS: Dict[str, Dict] = {
    'Models Database': {'path': MODELS_DB, 'port': 8881},
    'Usage Database': {'path': USAGE_DB, 'port': 8882},
    'Sessions Database': {'path': SESSIONS_DB, 'port': 8883},
    'Delete Database': {'action': 'delete_db'},
    'Kill Process on Port': {'action': 'kill_port'},
    'Exit': {'action': 'exit'}
}


def delete_database(db_path: Path) -> bool:
    """
    Safely delete a database file.

    Args:
        db_path: Path to the database file

    Returns:
        bool: True if database was deleted, False otherwise
    """
    try:
        if not db_path.exists():
            logger.warning(f"Database {db_path} does not exist")
            return False

        # Delete the database file
        os.remove(db_path)
        logger.info(f"Successfully deleted database: {db_path}")
        return True

    except Exception as e:
        logger.error(f"Error deleting database {db_path}: {e}")
        return False


def kill_port(port: int) -> bool:
    """
    Kill process running on specified port.

    Args:
        port: Port number to kill

    Returns:
        bool: True if process was killed, False otherwise
    """
    try:
        # Use lsof to find process using the port
        cmd = f"lsof -ti tcp:{port}"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        if output:
            pid = int(output.decode().strip())
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=3)
                logger.info(f"Successfully killed process {pid} on port {port}")
                return True
            except psutil.NoSuchProcess:
                logger.warning(f"Process {pid} on port {port} already terminated")
                return True
            except psutil.TimeoutExpired:
                proc.kill()
                logger.info(f"Force killed process {pid} on port {port}")
                return True
        else:
            logger.warning(f"No process found on port {port}")
            return False

    except Exception as e:
        logger.error(f"Error killing port {port}: {e}")
        return False


def cleanup_processes():
    """Terminate all running processes."""
    for process in running_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logger.error(f"Error while terminating process: {e}")
    running_processes.clear()


def signal_handler(signum, frame):
    """Handle termination signals."""
    print("\n🛑 Shutting down database viewers...")
    cleanup_processes()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def format_url(port: int) -> str:
    """Format URL with ANSI colors for terminal."""
    return f"\033[1;94mhttp://localhost:{port}\033[0m"


def start_datasette(
    db_path: str,
    start_port: int,
    max_attempts: int = 10
) -> Tuple[Optional[subprocess.Popen], Optional[int]]:
    """Try to start datasette on an available port with retries."""
    for port in range(start_port, start_port + max_attempts):
        # Try to kill any existing process on this port
        kill_port(port)
        time.sleep(1)  # Give the system time to free the port

        try:
            process = subprocess.Popen(
                [
                    "datasette", "serve", db_path,
                    "--port", str(port),
                    "--cors",
                    "--setting", "truncate_cells_html", "0"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Give the process a moment to start and bind to the port
            time.sleep(1)

            # Check if process is still running
            if process.poll() is None:
                # Try to connect to verify the server is up
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.connect(('localhost', port))
                        return process, port
                    except socket.error:
                        process.terminate()
                        continue
            else:
                # Process failed to start, clean up and try next port
                _, stderr = process.communicate()
                if b"address already in use" not in stderr:
                    print(f"Failed to start datasette: {stderr.decode()}")
                process.terminate()
        except Exception as e:
            print(f"Error starting datasette on port {port}: {e}")

    return None, None


def launch_viewer(db_path: str, db_name: str, start_port: int) -> bool:
    """Launch a database viewer and return success status."""
    print(f"🚀 Starting {db_name} database viewer...")
    process, port = start_datasette(db_path, start_port)
    if not process or not port:
        print(f"Failed to start {db_name} database viewer")
        return False

    running_processes.append(process)
    url = f"http://localhost:{port}"
    print(f"✓ {db_name} DB viewer: {format_url(port)}")

    # Open browser after a short delay to ensure server is ready
    time.sleep(1)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Note: Could not open browser automatically: {e}")
        print(f"Please open {url} manually in your browser")

    return True


def show_interactive_menu():
    """Show interactive menu for database selection."""
    while True:
        choice = questionary.select(
            "Select an action:",
            choices=list(DB_CONFIGS.keys())
        ).ask()

        if not choice:
            break

        config = DB_CONFIGS[choice]

        if 'action' in config:
            if config['action'] == 'kill_port':
                port = questionary.text("Enter port number to kill:").ask()
                if port:
                    try:
                        port = int(port)
                        if kill_port(port):
                            print(f"✓ Successfully killed process on port {port}")
                        else:
                            print(f"✗ No process found on port {port}")
                    except ValueError:
                        print("✗ Invalid port number")
            elif config['action'] == 'delete_db':
                db_choice = questionary.select(
                    "Select database to delete:",
                    choices=[
                        'Models Database',
                        'Usage Database',
                        'Sessions Database',
                        'Cancel'
                    ]
                ).ask()

                if db_choice == 'Cancel':
                    continue

                db_path = DB_CONFIGS[db_choice]['path']
                confirm = questionary.confirm(
                    f"Are you sure you want to delete {db_choice}? This action cannot be undone.",
                    default=False
                ).ask()

                if confirm:
                    if delete_database(db_path):
                        print(f"✓ Successfully deleted {db_choice}")
                    else:
                        print(f"✗ Failed to delete {db_choice}")
            elif config['action'] == 'exit':
                break
        else:
            if launch_viewer(config['path'], choice, config['port']):
                print("\n🔍 Press Ctrl+C to stop the server")
                running_processes[0].wait()
                break


@click.command()
@click.option('--db', is_flag=True, help='Launch interactive database viewer')
def cli(db):
    """Pydantic2 CLI tool for database viewing"""
    try:
        if db:
            show_interactive_menu()
        else:
            print("Use --db to launch the interactive database viewer")

    except Exception as e:
        print(f"Error: {str(e)}")
        cleanup_processes()
        raise click.Abort()


if __name__ == '__main__':
    try:
        cli()
    finally:
        cleanup_processes()
