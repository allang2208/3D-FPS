"""Dispatch this scoped import through Epic's local editor Python connection."""
import sys,time,json
from pathlib import Path
P=Path(__file__).parent
sys.path.insert(0,'E:/Program Files (x86)/UE_5.8/Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python')
import remote_execution as remote
client=remote.RemoteExecution()
try:
    client.start();time.sleep(2)
    node=next(n for n in client.remote_nodes if n['project_root'].replace('\\','/').rstrip('/')=='D:/FPS3D/FPSGAME')
    client.open_command_connection(node['node_id'])
    result=client.run_command(str(P/'import_live_editor.py'),raise_on_failure=False)
    (P/'live_import_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    if not result['success']:sys.exit(1)
finally:
    client.stop()
