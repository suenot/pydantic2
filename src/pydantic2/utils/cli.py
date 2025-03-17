import subprocess
import os
import click
import socket
import signal
import sys
import time
from typing import Optional, List, Tuple

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
            click.echo(f"Error while terminating process: {e}")
    running_processes.clear()


def signal_handler(signum, frame):
    """Handle termination signals."""
    click.echo("\nShutting down database viewers...")
    cleanup_processes()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def start_datasette(db_path: str, start_port: int, max_attempts: int = 10) -> Tuple[Optional[subprocess.Popen], Optional[int]]:
    """
    Try to start datasette on an available port with retries.
    Returns tuple of (process, port) or (None, None) if failed.
    """
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
                    click.echo(f"Failed to start datasette: {stderr.decode()}")
                process.terminate()
        except Exception as e:
            click.echo(f"Error starting datasette on port {port}: {e}")

    return None, None


@click.command()
@click.option('--view-models', is_flag=True, help='View models database')
@click.option('--view-usage', is_flag=True, help='View usage database')
@click.option('--view-all', is_flag=True, help='View both databases')
def cli(view_models, view_usage, view_all):
    """Pydantic2 CLI tool for database viewing"""
    try:
        if view_all:
            # Start models viewer
            models_process, models_port = start_datasette(MODELS_DB, 8001)
            if not models_process:
                click.echo("Failed to start models database viewer")
                return
            running_processes.append(models_process)
            click.echo(f"Started models DB viewer on port {models_port}")

            # Start usage viewer
            usage_process, usage_port = start_datasette(USAGE_DB, 8002)
            if not usage_process:
                click.echo("Failed to start usage database viewer")
                cleanup_processes()
                return
            running_processes.append(usage_process)
            click.echo(f"Started usage DB viewer on port {usage_port}")

            click.echo("\nPress Ctrl+C to stop the servers")

            # Monitor processes
            while True:
                try:
                    for proc in running_processes:
                        if proc.poll() is not None:
                            _, stderr = proc.communicate()
                            click.echo(f"Server terminated: {stderr.decode()}")
                            return
                    time.sleep(1)
                except KeyboardInterrupt:
                    break

        elif view_models:
            process, port = start_datasette(MODELS_DB, 8001)
            if not process:
                click.echo("Failed to start models database viewer")
                return
            running_processes.append(process)
            click.echo(f"Started models DB viewer on port {port}")
            process.wait()

        elif view_usage:
            process, port = start_datasette(USAGE_DB, 8002)
            if not process:
                click.echo("Failed to start usage database viewer")
                return
            running_processes.append(process)
            click.echo(f"Started usage DB viewer on port {port}")
            process.wait()

        else:
            click.echo("Specify an option: --view-models, --view-usage, or --view-all")

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        cleanup_processes()
        raise click.Abort()


if __name__ == '__main__':
    try:
        cli()
    finally:
        cleanup_processes()
