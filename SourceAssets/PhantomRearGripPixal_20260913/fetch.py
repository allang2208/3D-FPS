import subprocess,base64,json,urllib.request,urllib.parse
from pathlib import Path
P=Path(__file__).parent
remote='PhantomRearGripPixal20260913'
code="""$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.Encoding]::UTF8
@(Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/PhantomRearGripPixal20260913' -File | ForEach-Object { @{name=$_.Name;bytes=$_.Length} }) | ConvertTo-Json -Compress
"""
enc=base64.b64encode(code.encode('utf-16le')).decode()
result=subprocess.check_output(['ssh','-o','BatchMode=yes','r5080','powershell','-NoProfile','-EncodedCommand',enc],timeout=30)
files=json.loads(result.decode('utf-8-sig'))
if isinstance(files,dict):files=[files]
(P/'outputs.json').write_text(json.dumps(files,indent=2))
for f in files:
    name=f['name']
    if Path(name).name!=name:raise ValueError(name)
    url='http://192.168.3.142:8188/view?'+urllib.parse.urlencode({'filename':name,'subfolder':remote,'type':'output'})
    urllib.request.urlretrieve(url,P/name)
    print(name,f['bytes'],flush=True)
