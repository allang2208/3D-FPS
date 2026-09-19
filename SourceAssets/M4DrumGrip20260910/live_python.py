import sys,time,json
sys.path.insert(0,'E:/Program Files (x86)/UE_5.8/Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python')
import remote_execution
r=remote_execution.RemoteExecution();r.start()
try:
 for _ in range(20):
  nodes=[n for n in r.remote_nodes if n.get('project_name')=='FPSGAME']
  if nodes:break
  time.sleep(.25)
 if not nodes:raise RuntimeError('FPSGAME Python endpoint not found')
 r.open_command_connection(nodes[0]['node_id'])
 print(json.dumps(r.run_command(sys.argv[1],unattended=True),ensure_ascii=False))
finally:r.stop()
