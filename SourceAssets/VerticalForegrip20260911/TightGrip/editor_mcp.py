import urllib.request,json
from pathlib import Path
O=Path(__file__).parent
url='http://127.0.0.1:8000/mcp';headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
def rpc(method,params,rid=1):
 d={'jsonrpc':'2.0','method':method,'params':params}
 if rid is not None:d['id']=rid
 with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(d).encode(),headers=headers),timeout=45) as r:
  if r.headers.get('Mcp-Session-Id'):headers['Mcp-Session-Id']=r.headers['Mcp-Session-Id']
  s=r.read().decode()
  return json.loads(s) if s else {}
rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'grip-animation-refresh','version':'1'}})
rpc('notifications/initialized',{},None)
if __name__=='__main__':
 d=rpc('tools/list',{});(O/'editor_tools.json').write_text(json.dumps(d,indent=2));print(json.dumps(d)[:18000])
