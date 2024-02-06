import asyncio
import os
from rich.console import Console
import signal

from .stream_util import read_stream, read_stream_loading_bar
from .config import ConfigLoader, Process


class Runner:
    def __init__(self, config_file):
        self.work: list[Process] = ConfigLoader(config_file).get_config()
        self.raw_processes = []
        self.console = Console()
        self.console.print(f"Loaded {len(self.work)} proc contracts from {config_file}", style="blue")
        self.console.print(f"Runner.work: {self.work}", style="blue")

    async def run_proc(self, process: Process):
        self.console.print(f"Running proc: {process}", style="bold green")
        if process.before:
            await self.execute_before_script(process)

        if process.env:
            expanded_env = {k: os.path.expandvars(v) for k, v in process.env.items()}
            self.console.print(f"Injecting environment variables for {process.name}: {expanded_env}", style="bold purple")
            env = {**os.environ, **expanded_env}
        else:
            env = None

        print(f"process.name: {process.name}")
        cmd_process = await asyncio.create_subprocess_shell(
            process.cmd,
            cwd=process.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,  # This ensures the process runs in a new session
            env=env 
        )
        self.raw_processes.append(cmd_process)
        print(f"process.name: {process.name}")

        stdout_task = asyncio.create_task(read_stream(cmd_process.stdout, process.name, self.console))
        stderr_task = asyncio.create_task(read_stream_loading_bar(cmd_process.stderr, process.name, self.console))

        await asyncio.gather(stdout_task, stderr_task)
        return cmd_process

    async def execute_before_script(self, process: Process):
        self.console.print(f"Executing before script for [{process.name}] : [ {process.before} ]", style="bold yellow")
        before_process = await asyncio.create_subprocess_shell(
            process.before,
            cwd=process.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        await before_process.wait()  # Wait for the before script to complete


    async def inject_env_vars(self, process: Process):
        self.console.print(f"Injecting environment variables for [ {process.name} ]: [ {process.environment} ]", style="bold yellow")
        os.environ.update(process.environment)

    async def run_all_services(self):
        tasks = [self.run_proc(proc) for proc in self.work]
        self.raw_processes = await asyncio.gather(*tasks)  # Store processes for potential termination
    
    async def terminate_processes(self):
        self.console.print("Attempting to terminate processes...", style="bold red")
        for proc in self.raw_processes:
            if proc and hasattr(proc, 'pid'):
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)  # Send SIGTERM to the process group
                    # Use asyncio.create_task to ensure we're not waiting here if the loop is closing
                    termination_task = asyncio.create_task(proc.wait())
                    await asyncio.wait_for(termination_task, timeout=5)
                    self.console.print(f"[{proc.pid}] Process terminated gracefully", style="bold green")
                except asyncio.TimeoutError:
                    os.killpg(pgid, signal.SIGKILL)  # Force kill if not responding
                    await proc.wait()
                    self.console.print(f"[{proc.pid}] Process killed forcefully", style="bold red")
                except Exception as e:
                    self.console.print(f"[{proc.pid}] Error terminating process: {e}", style="bold red")
