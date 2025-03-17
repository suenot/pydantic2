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
                ["datasette", db_path, "--port", str(port)],
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


@click.command()
@click.option('--view-models', is_flag=True, help='View models database')
@click.option('--view-usage', is_flag=True, help='View usage database')
@click.option('--view-all', is_flag=True, help='View both databases')
def cli(view_models, view_usage, view_all):
    """Pydantic2 CLI tool for database viewing"""
    try:
        if view_all:
            print("🚀 Starting database viewers...")

            # Start models viewer
            models_process, models_port = start_datasette(MODELS_DB, 8001)
            if not models_process or not models_port:
                print("Failed to start models database viewer")
                return
            running_processes.append(models_process)
            print(f"✓ Models DB viewer: {format_url(models_port)}")

            # Start usage viewer
            usage_process, usage_port = start_datasette(USAGE_DB, 8002)
            if not usage_process or not usage_port:
                print("Failed to start usage database viewer")
                cleanup_processes()
                return
            running_processes.append(usage_process)
            print(f"✓ Usage DB viewer: {format_url(usage_port)}")

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

        elif view_models:
            print("🚀 Starting models database viewer...")
            process, port = start_datasette(MODELS_DB, 8001)
            if not process or not port:
                print("Failed to start models database viewer")
                return
            running_processes.append(process)
            print(f"✓ Models DB viewer: {format_url(port)}")
            print("\n🔍 Press Ctrl+C to stop the server")
            process.wait()

        elif view_usage:
            print("🚀 Starting usage database viewer...")
            process, port = start_datasette(USAGE_DB, 8002)
            if not process or not port:
                print("Failed to start usage database viewer")
                return
            running_processes.append(process)
            print(f"✓ Usage DB viewer: {format_url(port)}")
            print("\n🔍 Press Ctrl+C to stop the server")
            process.wait()

        else:
            print("Specify an option: --view-models, --view-usage, or --view-all")

    except Exception as e:
        print(f"Error: {str(e)}")
        cleanup_processes()
        raise click.Abort()


if __name__ == '__main__':
    try:
        cli()
    finally:
        cleanup_processes()
