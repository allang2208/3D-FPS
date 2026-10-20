"""Task-local callback socket; still invoked under the standard bridge mutex."""
from pathlib import Path
import socket

_source=Path('E:/Program Files (x86)/UE_5.8/Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python/remote_execution.py')
exec(compile(_source.read_text(encoding='utf-8-sig'),str(_source),'exec'))
_RemoteExecution=RemoteExecution
class RemoteExecution(_RemoteExecution):
    def __init__(self):
        config=RemoteExecutionConfig()
        config.command_endpoint=('127.0.0.1',0)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
            probe.bind(config.command_endpoint)
            config.command_endpoint=probe.getsockname()
        super().__init__(config)
