"""Isolated UE listen server, remote customer, second profile and original customer reconnect."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time


root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--engine',type=Path,default=Path('E:/Program Files (x86)/UE_5.8'))
parser.add_argument('--module',type=Path,default=root/'Binaries/Win64/UnrealEditor-FPSGAME.dll')
parser.add_argument('--run',default=time.strftime('%Y%m%d-%H%M%S'))
parser.add_argument('--port',type=int,default=0)
parser.add_argument('--guards-only', action='store_true')
args = parser.parse_args()
run = root/'Saved/ArtisanVillageNetwork'/args.run
host = run/'Host'
evidence = run/'Evidence'
evidence.mkdir(parents=True,exist_ok=False)
(host/'Binaries/Win64').mkdir(parents=True)
shutil.copy2(root/'FPSGAME.uproject',host/'FPSGAME.uproject')
shutil.copytree(root/'Config',host/'Config')
for name in ('Content','Plugins','Shaders'):
    subprocess.run(['cmd','/d','/c','mklink','/J',str(host/name),str(root/name)],check=True,stdout=subprocess.DEVNULL)
shutil.copy2(args.module,host/'Binaries/Win64/UnrealEditor-FPSGAME.dll')
shutil.copy2(root/'Binaries/Win64/UnrealEditor.modules',host/'Binaries/Win64/UnrealEditor.modules')
exe = args.engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
    probe.bind(('127.0.0.1',args.port))
    port = probe.getsockname()[1]
peers = {}


def launch(role):
    profile = 'owner' if role=='rejoin' else role
    user_dir = run/profile
    user_dir.mkdir(exist_ok=True)
    authority = role=='server'
    url = '/Game/GameMaps/L_TemperateHills_Initial?listen' if authority else '127.0.0.1:'+str(port)
    cmd = [str(exe),str(host/'FPSGAME.uproject'),url,'-game',
           '-nullrhi','-nosound','-unattended','-nosplash','-Multiprocess','-NoAssetRegistryCacheWrite',
           '-AssetGatherAll=false','-SkipStartupMenu','-ClearwaterNoMenu','-NoSplash',
           '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
           '-ArtisanVillageTest','-ArtisanRole='+role,'-ArtisanEvidence='+str(evidence),'-port='+str(port),
           '-UserDir='+str(user_dir),'-abslog='+str(run/(role+'.log')),
           '-ColdSteelProfile=ArtisanVillage_'+args.run+'_'+profile,
           '-ExecCmds=t.MaxFPS 30,fps.body.WorldBodySuppress 1,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.ArtisanVillageNet',
           '-ini:Game:[TemperateHills.NightRaid]:Enabled=False',
           '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
           '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
           '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
           '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False']
    if authority:
        cmd.extend(['-HillsNewWorld','-HillsSeed=1518277816'])
    if args.guards_only:
        cmd.append('-ArtisanGuardOnly')
    peers[role] = subprocess.Popen(cmd,creationflags=subprocess.CREATE_NO_WINDOW)
    print(role,peers[role].pid,port,flush=True)


def wait_for(role,case):
    file = evidence/(role+'.'+case+'.json')
    deadline = time.monotonic()+1100
    while not file.exists():
        for failed in evidence.glob('*.json'):
            data = json.loads(failed.read_bytes())
            if not data['passed']:
                raise RuntimeError(str(data))
        for watched in {role,'server'}:
            if peers[watched].poll() is not None:
                raise RuntimeError(f'{watched} exited before {role}.{case}: '+str(peers[watched].returncode))
        if time.monotonic()>deadline:
            raise TimeoutError(f'{role} did not reach {case}')
        time.sleep(2)
    data = json.loads(file.read_bytes())
    if not data['passed']:
        raise RuntimeError(str(data))
    return data


def close_after_ack(role):
    try:
        peers[role].wait(timeout=35)
    except subprocess.TimeoutExpired:
        stop(role)


def stop(role):
    peer=peers[role]
    if peer.poll() is None:
        peer.terminate()
    peer.wait(timeout=30)


result = dict(passed=False, port=port, mode='listen', rendered=False,
              module_sha256=hashlib.sha256((host/'Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest())
try:
    launch('server')
    deadline=time.monotonic()+850
    while True:
        log = run/'server.log'
        if log.exists() and f'IpNetDriver listening on port {port}' in log.read_text(errors='replace'):
            break
        if peers['server'].poll() is not None or time.monotonic()>deadline:
            raise RuntimeError('listen server did not bind its UDP port')
        time.sleep(2)
    launch('owner')
    if args.guards_only:
        result['scope'] = 'guard combat'
        result['passed'] = wait_for('server','done')['passed']
    else:
        wait_for('owner','done')
        first=wait_for('server','personal-carpenter')
        close_after_ack('owner')
        launch('visitor')
        second=wait_for('visitor','profile')
        wait_for('server','visitor-authority')
        close_after_ack('visitor')
        launch('rejoin')
        restored=wait_for('rejoin','profile')
        wait_for('server','rejoin-authority')
        wait_for('server','done')
        result['identities_distinct_and_restored'] = first['detail']==restored['detail'] and first['detail']!=second['detail']
        result['passed']=result['identities_distinct_and_restored']
except Exception as exc:
    result['error']=str(exc)
finally:
    for role in reversed(peers):
        stop(role)
    result['checks']=[json.loads(p.read_bytes()) for p in sorted(evidence.glob('*.json'))]
    (run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('RESULT',result['passed'],run,flush=True)
raise SystemExit(0 if result['passed'] else 1)
