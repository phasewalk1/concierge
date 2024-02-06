from typing import Optional
import yaml



class Process:
    name: str
    cwd: str
    cmd: str
    before: Optional[str]
    env: Optional[dict]

    def __init__(self, name, cwd, cmd, before=None, env=None):
        self.name = name
        self.cwd = cwd
        self.cmd = cmd
        self.before = before
        self.env = env


class ConfigLoader:
    def __init__(self, config_file="concierge.yml"):
        self.config_file = config_file
        self.processes: list[Process]= []
        self.load_config()
    
    
    def get_config(self) -> list[Process]:
        if not self.processes:
            self.load_config()
        return self.processes
    
    def load_config(self):
        with open(self.config_file, 'r') as file:
            config = yaml.safe_load(file)

        work = config.get('work', [])
        for name, service_config in work.items():
            self.processes.append(Process(
                name=name,
                cwd=service_config.get('cwd', '.'),
                cmd=service_config['cmd'],
                before=service_config.get('before', None),
                # this is a list[dict[]], we want a dict[]
                env=service_config.get('env', None).pop() if service_config.get('env', None) else None
            ))

        for proc in self.processes:
            print(f"<config-loader> Loaded config for proc --> {proc.name}")