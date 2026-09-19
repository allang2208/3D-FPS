import json,urllib.request,urllib.parse,sys,subprocess,base64
from pathlib import Path
P=Path(__file__).parent;B='http://192.168.3.142:8188'
pid=json.loads((P/'receipt.json').read_text())['prompt_id']
h=json.load(urllib.request.urlopen(B+'/history/'+pid,timeout=15))
if pid not in h:
 q=json.load(urllib.request.urlopen(B+'/queue',timeout=15));print({k:[x[1] for x in v] for k,v in q.items()});sys.exit()
(P/'history.json').write_text(json.dumps(h,indent=2));print(h[pid]['status'])
if h[pid]['status']['status_str']!='success':sys.exit(1)
root=(P/'remote_root.txt').read_text(encoding='utf-8');remote=root+'\\output\\VerticalForegrip20260911'
code="[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-ChildItem -LiteralPath '"+remote+"' -File | Select-Object Name,Length | ConvertTo-Json -Compress)))"
r=subprocess.run(['ssh','-o','BatchMode=yes','r5080','powershell','-NoProfile','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],capture_output=True,timeout=20)
files=json.loads(base64.b64decode(r.stdout.strip()).decode('utf-8'));files=files if isinstance(files,list) else [files]
for f in files:
 dst=P/f['Name']
 if not dst.exists():urllib.request.urlretrieve(B+'/view?'+urllib.parse.urlencode({'filename':f['Name'],'subfolder':'VerticalForegrip20260911','type':'output'}),dst)
 print(dst.name,dst.stat().st_size)
