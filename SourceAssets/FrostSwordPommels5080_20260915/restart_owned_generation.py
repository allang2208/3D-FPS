"""Recover our saved jobs when the custom node ignores targeted interruption."""
import json,subprocess,base64,time,urllib.request,shutil
from pathlib import Path
P=Path(__file__).parent;BASE='http://192.168.3.142:8188';KEYS=['ballast_hardened','ballast_rune','ballast_magic_orb']
def req(path,data=None):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'}),timeout=20) as r:raw=r.read()
    return json.loads(raw) if raw else {}
owned=set()
for key in KEYS:
    for path in [P/key/'receipt.json',P/key/'ss64_attempt/receipt.json']:owned.add(json.loads(path.read_text())['prompt_id'])
queue=req('/queue')
if any(job[1] not in owned for job in queue['queue_running']+queue['queue_pending']):raise RuntimeError('Another task is present; leave the shared service running')
(P/'queue_before_owned_restart.json').write_text(json.dumps(queue,indent=2))
script=r'''
$ErrorActionPreference='Stop'
$root='D:\开发文件\ComfyUI'
$queue=Invoke-RestMethod 'http://127.0.0.1:8188/queue'
$owned=__OWNED__
foreach($job in @($queue.queue_running)+@($queue.queue_pending)){if($job[1] -notin $owned){throw 'Another task appeared; restart cancelled'}}
$listeners=Get-NetTCPConnection -LocalPort 8188 -State Listen
foreach($listenerId in ($listeners.OwningProcess | Sort-Object -Unique)){
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$listenerId"
    if($process.Name -ne 'python.exe' -or $process.CommandLine -notlike '*main.py*--port 8188*'){throw 'Unexpected process; not stopping'}
    Stop-Process -Id $listenerId -Force
}
$python=Join-Path $root '.venv\Scripts\python.exe'
$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$started=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine=('"'+$python+'" "D:\Mechanical3DSetup\launch_comfy.py" "'+$root+'"')
    CurrentDirectory=$root
    ProcessStartupInformation=$startup
}
if($started.ReturnValue -ne 0){throw 'ComfyUI launch failed'}
Write-Output 'OWNED_GENERATION_SERVICE_RESTARTED'
'''.replace('__OWNED__','@('+','.join("'"+v+"'" for v in owned)+')')
code=base64.b64encode(script.encode('utf-16-le')).decode()
result=subprocess.run(['ssh','-o','ConnectTimeout=10','r5080','powershell','-NoProfile','-EncodedCommand',code],capture_output=True)
(P/'owned_restart.log').write_bytes(result.stdout+result.stderr)
if result.returncode:raise RuntimeError('Recovery stopped; see owned_restart.log')
for attempt in range(24):
    try:req('/system_stats');break
    except Exception:time.sleep(5)
else:raise RuntimeError('Service not ready')
for key in KEYS:
    folder=P/key;shutil.copy2(folder/'receipt.json',folder/'receipt_before_service_restart.json')
    w=json.loads((folder/'workflow.json').read_text());receipt=req('/prompt',{'client_id':'FrostSwordPommels5080_20260915','prompt':w});receipt['attempt']='ss32_recovered'
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2));print(key,receipt,flush=True)
