import os,json,time,subprocess,base64,hashlib
os.environ['COMFY_BASE_URL']='http://192.168.3.142:8188'
from pipeline import P,req,download
receipt=json.loads((P/'magic_dust_high_recovery_submitted.json').read_text(encoding='utf-8-sig'));pid=receipt['prompt_id']
def remote(code):
 encoded=base64.b64encode(code.encode('utf-16le')).decode()
 return subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','r5080','powershell','-NoProfile','-EncodedCommand',encoded],timeout=30).decode('utf-8-sig')
(P/'recovery_system_stats.json').write_text(json.dumps(req('/system_stats'),indent=2))
while True:
 h=req('/history/'+pid)
 if pid in h:
  h=h[pid];(P/'magic_dust_high_recovery_history.json').write_text(json.dumps(h,indent=2))
  print(h['status'],flush=True)
  if h['status']['status_str']!='success':break
  files=json.loads(remote("@(Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/EnhancementMaterials20260911' -Filter 'magic_dust_high*.glb' | ForEach-Object { @{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} }) | ConvertTo-Json -Compress"))
  if isinstance(files,dict):files=[files]
  (P/'recovery_remote_outputs.json').write_text(json.dumps(files,indent=2))
  for f in files:
   download(f['name']);assert hashlib.sha256((P/f['name']).read_bytes()).hexdigest().upper()==f['sha256']
  print('RECOVERY_DOWNLOAD_VERIFIED',flush=True);break
 stats=remote('nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader').strip()
 with (P/'recovery_vram_samples.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'gpu':stats})+'\n')
 print('running',stats,flush=True);time.sleep(60)
