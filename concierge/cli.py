import asyncio
import signal
import click
from rich.console import Console

from .runner import Runner

console = Console()
processes = []


@click.command()
@click.argument('config_file', type=click.Path(exists=True), default="concierge.yml")
def cli(config_file):
    runner = Runner(config_file)
    try:
        asyncio.run(runner.run_all_services())
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught. Terminating processes...")
        asyncio.run(runner.terminate_processes())


if __name__ == '__main__':
    cli()

