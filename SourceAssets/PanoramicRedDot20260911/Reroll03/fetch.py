import subprocess,base64,json,hashlib,urllib.request,urllib.parse,sys
from run import P,req,REMOTE
mode=sys.argv[1] if len(sys.argv)>1 else 'generate'
pid=json.loads((P/(mode+'_receipt.json')).read_text())['prompt_id']
h=req('/history/'+pid)[pid];assert h['status']['status_str']=='success'
(P/(mode+'_history.json')).write_text(json.dumps(h,indent=2))
code="@(Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/PanoramicRedDot20260911/Reroll03' -Filter '*.glb' | ForEach-Object { @{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash} }) | ConvertTo-Json -Compress"
encoded=base64.b64encode(code.encode('utf-16le')).decode()
files=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','r5080','powershell','-NoProfile','-EncodedCommand',encoded]).decode('utf-8-sig'))
if isinstance(files,dict):files=[files]
for f in files:
 url='http://192.168.3.142:8188/view?'+urllib.parse.urlencode({'filename':f['name'],'subfolder':REMOTE,'type':'output'})
 urllib.request.urlretrieve(url,P/f['name']);assert hashlib.sha256((P/f['name']).read_bytes()).hexdigest().upper()==f['sha256'];print('verified',f['name'],f['bytes'])
(P/'download_manifest.json').write_text(json.dumps(files,indent=2))
