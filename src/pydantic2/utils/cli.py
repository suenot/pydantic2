import subprocess
import os
import click
import socket
import signal
import sys
import time
import colorlog
import logging
from typing import Optional, List, Tuple

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

BASE_DIR = os.path.dirname(__file__)
MODELS_DB = os.path.abspath(os.path.join(BASE_DIR, "../db/models.db"))
USAGE_DB = os.path.abspath(os.path.join(BASE_DIR, "../db/usage.db"))
SESSIONS_DB = os.path.abspath(os.path.join(BASE_DIR, "../db/sessions.db"))

# Global list to track running processes
running_processes: List[subprocess.Popen] = []


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
    print(f"✓ {db_name} DB viewer: {format_url(port)}")
    return True


@click.command()
@click.option('--view-models', is_flag=True, help='View models database')
@click.option('--view-usage', is_flag=True, help='View usage database')
@click.option('--view-sessions', is_flag=True, help='View sessions database')
@click.option('--view-all', is_flag=True, help='View all databases')
def cli(view_models, view_usage, view_sessions, view_all):
    """Pydantic2 CLI tool for database viewing"""
    try:
        # Configuration for each database
        db_configs = {
            'models': {'path': MODELS_DB, 'port': 8001, 'view': view_models},
            'usage': {'path': USAGE_DB, 'port': 8002, 'view': view_usage},
            'sessions': {'path': SESSIONS_DB, 'port': 8003, 'view': view_sessions}
        }

        if view_all:
            print("🚀 Starting all database viewers...")

            # Launch all viewers
            for db_name, config in db_configs.items():
                if not launch_viewer(config['path'], db_name, config['port']):
                    cleanup_processes()
                    return

            print("\n🔍 Press Ctrl+C to stop the servers")

            # Monitor processes
            while True:
                try:
                    for proc in running_processes:
                        if proc.poll() is not None:
                            _, stderr = proc.communicate()
                            print(f"Server terminated: {stderr.decode()}")
                            return
                    time.sleep(1)
                except KeyboardInterrupt:
                    break

        # Launch individual viewers if requested
        elif any([view_models, view_usage, view_sessions]):
            for db_name, config in db_configs.items():
                if config['view']:
                    if launch_viewer(config['path'], db_name, config['port']):
                        print("\n🔍 Press Ctrl+C to stop the server")
                        running_processes[0].wait()
                    return
        else:
            print(
                "Specify an option: "
                "--view-models, --view-usage, --view-sessions, or --view-all"
            )

    except Exception as e:
        print(f"Error: {str(e)}")
        cleanup_processes()
        raise click.Abort()


if __name__ == '__main__':
    try:
        cli()
    finally:
        cleanup_processes()
