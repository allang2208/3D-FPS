"""Execute the scoped import in the existing editor over loopback Python."""
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(r'D:\FPS3D\FPSGAME')
CLIENT = Path(r'E:\Program Files (x86)\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py')
spec = importlib.util.spec_from_file_location('ue_pickaxe_remote', CLIENT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
config = client.RemoteExecutionConfig()
config.command_endpoint = ('127.0.0.1', 6789)
remote = client.RemoteExecution(config)
remote.start()
try:
    # Give the shared editor time to finish its current main-thread operation.
    deadline = time.monotonic()+45
    nodes = []
    while time.monotonic() < deadline:
        nodes = [n for n in remote.remote_nodes if n.get('project_name') == 'FPSGAME']
        if nodes:
            break
        time.sleep(.2)
    if len(nodes) != 1:
        raise RuntimeError('No unique FPSGAME editor on loopback: '+str(nodes))
    remote.open_command_connection(nodes[0]['node_id'])
    result = remote.run_command(str(ROOT/'Tools/Production/import_pickaxe_overhead.py'), exec_mode=client.MODE_EXEC_FILE)
    print(json.dumps(result), flush=True)
    (Path(__file__).parent/'editor_import_response.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not result.get('success'):
        raise RuntimeError('Editor import failed; see response')
finally:
    remote.stop()
