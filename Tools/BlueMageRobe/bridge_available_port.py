"""Task-local client using an available loopback command port; caller holds UE gate."""
import sys,socket,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'AssetPipeline'))
import ue_python_exec
client=ue_python_exec.load_client(ue_python_exec.DEFAULT_REMOTE_EXEC)
with socket.socket() as sock:
 sock.bind(('127.0.0.1',0));endpoint=sock.getsockname()
cfg=client.RemoteExecutionConfig();cfg.command_endpoint=endpoint
remote=client.RemoteExecution(cfg);remote.start()
try:
 deadline=time.monotonic()+6
 while not remote.remote_nodes and time.monotonic()<deadline:time.sleep(.1)
 node=ue_python_exec.pick_node(remote.remote_nodes,None)
 if not node:raise RuntimeError('No unique FPSGAME editor')
 remote.open_command_connection(node['node_id'])
 result=remote.run_command(str(Path(sys.argv[1]).resolve()),exec_mode=client.MODE_EXEC_FILE)
 print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result.get('success') else 1)
finally:remote.stop()
