"""Print the remote-execution node id of the editor whose project_root is D:/FPS3D/FPSGAME/.

FPSGAME-mp editors report the same project_name ("FPSGAME"); project_root tells them apart.
Exit 3 when no matching editor answers.
"""
import importlib.util
import sys
import time

REMOTE = r'E:\Program Files (x86)\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py'
spec = importlib.util.spec_from_file_location('ue_remote_execution', REMOTE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
remote = module.RemoteExecution()
remote.start()
try:
    deadline = time.time() + 8
    while time.time() < deadline:
        match = [n for n in remote.remote_nodes
                 if str(n.get('project_root', '')).replace('\\', '/').rstrip('/').lower() == 'd:/fps3d/fpsgame']
        if match:
            print(match[0]['node_id'])
            sys.exit(0)
        time.sleep(0.3)
    sys.exit(3)
finally:
    remote.stop()
