import subprocess,base64,json,hashlib,urllib.request,urllib.parse
from pathlib import Path
from pipeline import P,BASE,REMOTE,TAG,req,save

pid=json.loads((P/(TAG+'_submitted.json')).read_text())['prompt_id']
h=req('/history/'+pid)
assert pid in h and h[pid]['status']['status_str']=='success', 'Generation has not completed successfully'
save(TAG+'_history.json',h[pid])
code=r"""$ProgressPreference='SilentlyContinue'
@(Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/ReferenceStock20260912' -File | ForEach-Object { @{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} }) | ConvertTo-Json -Compress
"""
encoded=base64.b64encode(code.encode('utf-16le')).decode()
out=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','r5080','powershell','-NoProfile','-EncodedCommand',encoded],timeout=50)
files=json.loads(out.decode('utf-8-sig').strip() or '[]')
if isinstance(files,dict):files=[files]
save('remote_outputs.json',files)
for f in files:
    name=f['name'];assert Path(name).name==name
    target=P/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest().upper()==f['sha256']:continue
    url=BASE+'/view?'+urllib.parse.urlencode({'filename':name,'subfolder':REMOTE,'type':'output'})
    urllib.request.urlretrieve(url,target)
    assert hashlib.sha256(target.read_bytes()).hexdigest().upper()==f['sha256']
    print('Verified',name,f['bytes'],flush=True)
