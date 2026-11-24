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
parser.add_argument('--shop-scene', action='store_true')
parser.add_argument('--smith-lesson', action='store_true')
parser.add_argument('--pew', action='store_true')
parser.add_argument('--render-server', action='store_true', help='render the shop-distance host offscreen with D3D12 at 1920x1080')
args = parser.parse_args()
if args.render_server and not (args.shop_scene or args.smith_lesson):
    parser.error('--render-server requires --shop-scene or --smith-lesson')
run = root/'Saved/ArtisanVillageNetwork'/args.run
host = run/'Host'
evidence = run/'Evidence'
evidence.mkdir(parents=True,exist_ok=False)
(host/'Binaries/Win64').mkdir(parents=True)
shutil.copy2(root/'FPSGAME.uproject',host/'FPSGAME.uproject')
shutil.copytree(root/'Config',host/'Config')
def junction(destination, source):
    subprocess.run(['cmd','/d','/c','mklink','/J',str(destination),str(source)],check=True,stdout=subprocess.DEVNULL)

for name in ('Content','Shaders'):
    junction(host/name,root/name)
(host/'Plugins').mkdir()
for plugin in (root/'Plugins').iterdir():
    if not plugin.is_dir():
        continue
    dest=host/'Plugins'/plugin.name
    if not (plugin/'Binaries/Win64/UnrealEditor.modules').is_file():
        junction(dest,plugin)
        continue
    dest.mkdir()
    for item in plugin.iterdir():
        if item.name in ('Intermediate','Saved','Source'):
            continue
        if item.name=='Binaries':
            shutil.copytree(item,dest/item.name,ignore=shutil.ignore_patterns('*.pdb','*.exp','*.lib'))
        elif item.is_dir():
            junction(dest/item.name,item)
        else:
            shutil.copy2(item,dest/item.name)
manifest = root/'Binaries/Win64/UnrealEditor.modules'
for name, filename in json.loads(manifest.read_text(encoding='utf-8-sig'))['Modules'].items():
    source = args.module if name == 'FPSGAME' else manifest.parent/filename
    shutil.copy2(source, host/'Binaries/Win64'/filename)
shutil.copy2(manifest, host/'Binaries/Win64'/manifest.name)
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
    if args.shop_scene:
        cmd.append('-ArtisanShopScene')
    if args.shop_scene or args.smith_lesson:
        if authority and args.render_server:
            cmd.remove('-nullrhi')
            cmd=[arg.replace('fps.body.WorldBodySuppress 1,','') for arg in cmd]
            cmd.extend(['-d3d12','-RenderOffScreen','-ResX=1920','-ResY=1080','-ForceRes'])
        else:
            cmd.append('-NoShaderCompile')
    if args.smith_lesson:
        cmd.append('-SmithLessonScene')
    if args.pew:
        cmd.extend(['-ArtisanPew','-NoShaderCompile'])
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


result = dict(passed=False, port=port, mode='listen', rendered=args.render_server,
              module_sha256=hashlib.sha256((host/'Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest())
village_map = host/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
result['village_map_sha256_at_start'] = hashlib.sha256(village_map.read_bytes()).hexdigest()
try:
    launch('server')
    deadline=time.monotonic()+(2100 if args.render_server else 850)
    while True:
        log = run/'server.log'
        status = log.read_text(errors='replace') if log.exists() else ''
        if f'IpNetDriver listening on port {port}' in status and (not args.render_server or 'HILLS_READY seed=' in status):
            break
        if peers['server'].poll() is not None or time.monotonic()>deadline:
            raise RuntimeError('listen server did not reach its launch checkpoint')
        time.sleep(2)
    launch('owner')
    if args.smith_lesson:
        result['scope']='shop lamps, two furnaces, owner-only mining lesson, pickup, delivery and reconnect'
        wait_for('owner','delivered')
        stop('owner')
        wait_for('server','disconnected')
        launch('rejoin')
        wait_for('rejoin','restored')
        result['passed']=wait_for('server','done')['passed']
    elif args.pew:
        result['scope']='two players on the installed outdoor chapel pew; authority interaction and replicated slots'
        wait_for('owner','both-standing')
        result['passed']=wait_for('server','done')['passed']
    elif args.shop_scene:
        result['scope'] = 'shop repair, shared chest and near/far/return on real streamed village'
        wait_for('owner','returned')
        stop('owner')
        wait_for('server','disconnected')
        launch('rejoin')
        wait_for('rejoin','late-layout')
        result['passed']=wait_for('server','done')['passed']
    elif args.guards_only:
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
        try:
            stop(role)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result.setdefault('shutdown_errors', {})[role]=str(exc)
            result['passed']=False
    result['checks']=[json.loads(p.read_bytes()) for p in sorted(evidence.glob('*.json'))]
    (run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('RESULT',result['passed'],run,flush=True)
raise SystemExit(0 if result['passed'] else 1)
