import subprocess,base64,json,hashlib
from pipeline import P,download,req
code="""$ProgressPreference='SilentlyContinue'
@(Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/MagicScroll20260911' -Filter '*.glb' -ErrorAction SilentlyContinue | ForEach-Object { @{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} }) | ConvertTo-Json -Compress
"""
encoded=base64.b64encode(code.encode('utf-16le')).decode()
out=subprocess.check_output(['ssh','-o','BatchMode=yes','r5080','powershell','-NoProfile','-EncodedCommand',encoded])
files=json.loads(out.decode('utf-8-sig').strip() or '[]')
if isinstance(files,dict): files=[files]
(P/'remote_outputs.json').write_text(json.dumps(files,indent=2))
complete=[]
for receipt in P.glob('*_submitted.json'):
    pid=json.loads(receipt.read_text())['prompt_id'];h=req('/history/'+pid)
    if pid in h:
        (P/receipt.name.replace('_submitted','_history')).write_text(json.dumps(h[pid],indent=2))
        if h[pid]['status']['status_str']=='success': complete.append(receipt.stem.replace('_submitted',''))
for f in files:
    if not any(f['name'].startswith(tag+'_') for tag in complete): continue
    dest=P/f['name']
    if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest().upper()!=f['sha256']:
        download(f['name'])
    assert hashlib.sha256(dest.read_bytes()).hexdigest().upper()==f['sha256']
    print('verified',f['name'])
