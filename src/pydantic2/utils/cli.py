import subprocess
import os
import click

BASE_DIR = os.path.dirname(__file__)
MODELS_DB = os.path.abspath(os.path.join(BASE_DIR, "../db/models.db"))
USAGE_DB = os.path.abspath(os.path.join(BASE_DIR, "../db/usage.db"))


@click.command()
@click.option('--view-models', is_flag=True, help='View models database')
@click.option('--view-usage', is_flag=True, help='View usage database')
@click.option('--view-all', is_flag=True, help='View both databases')
def cli(view_models, view_usage, view_all):
    """Pydantic2 CLI tool for database viewing"""
    if view_all:
        subprocess.Popen(["datasette", MODELS_DB, "--port", "8001"])
        subprocess.Popen(["datasette", USAGE_DB, "--port", "8002"])
    elif view_models:
        subprocess.run(["datasette", MODELS_DB, "--port", "8001"])
    elif view_usage:
        subprocess.run(["datasette", USAGE_DB, "--port", "8002"])
    else:
        click.echo("Specify an option: --view-models, --view-usage, or --view-all")


if __name__ == '__main__':
    cli()
