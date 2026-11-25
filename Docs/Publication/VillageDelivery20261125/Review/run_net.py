import argparse, csv, json, os, socket, subprocess, time
from pathlib import Path
r=Path(__file__).parent
opts=argparse.ArgumentParser(description=__doc__)
opts.add_argument('--engine-cmd',type=Path,required=True)
opts.add_argument('--project',type=Path,required=True,help='isolated project using the current module')
opts.add_argument('--previous-project',type=Path,required=True,help='isolated project using the older module')
opts.add_argument('--out',type=Path,required=True)
cfg=opts.parse_args()
exe=cfg.engine_cmd.resolve()
project=cfg.project.resolve()
previous=cfg.previous_project.resolve()
if r.resolve().parents[3]/'FPSGAME.uproject' in (project,previous):
    raise SystemExit('Use isolated hosts for the new-world repair fixture')
if project==previous or not all(p.is_file() for p in (exe,project,previous)):
    raise SystemExit('Two isolated project files and the commandlet executable are required')
out=cfg.out.resolve()
out.mkdir(parents=True,exist_ok=False)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
    s.bind(('127.0.0.1',0));port=s.getsockname()[1]
def start(role):
    d=out/role;d.mkdir(parents=True,exist_ok=True)
    host=role=='host'
    url='/Game/GameMaps/L_ForestPathVillage?listen?HillsNewWorld' if host else '127.0.0.1:'+str(port)
    args=[str(exe),str(project),url,'-game','-nullrhi','-nosound','-unattended','-NoSplash','-Multiprocess',
          '-DisablePlugins=FPSStandaloneRuntime','-SkipStartupMenu','-ClearwaterNoMenu','-GameLoadingMode=Quick',
          '-HillsSeed=51748691','-port='+str(port),'-multihome=127.0.0.1','-VillageDeliveryReview','-VillageDeliveryOutput='+str(d),
          '-ExecCmds=t.MaxFPS 36,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,py "'+str(r/'boot.py')+'"','-corelimit=4',
          '-asynctexturecompilationmaxconcurrency=1','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
          '-ColdSteelProfile=VillageDelivery_'+('host' if host else 'guest'),'-UserDir='+str(out/('hostUser' if host else 'clientUser')),
          '-abslog='+str(d/'game.log'),

          '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
          '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
          '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
          '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False']
    if host:args.append('-HillsNewWorld')
    if role=='mismatch':
        args[1]=str(previous)
        args=[v for v in args if not v.startswith('-ExecCmds=')]
        args.append('-ExecCmds=t.MaxFPS 20')
    env=dict(os.environ,VILLAGE_AUDIT_EVIDENCE=str(out),VILLAGE_AUDIT_ROLE=role,VILLAGE_AUDIT_SCRIPT=str(r/'peer.py'))
    p=subprocess.Popen(args,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    (d/'pid.txt').write_text(str(p.pid));return p
def load(path):return json.loads(path.read_text(encoding='utf8'))
def wait(seconds,predicate):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        for role,p in peers.items():
            if (out/role/'error.json').exists():raise RuntimeError((out/role/'error.json').read_text())
            if p.poll() is not None and not any((out/role/k).exists() for k in ('accepted.json','rejoined.json','finish.json')):
                raise RuntimeError(role+' exited early: '+str(p.returncode))
        time.sleep(2)
    raise TimeoutError(str(out))
peers={}
try:
    peers['host']=start('host')
    wait(480,lambda:(out/'host/progress.json').exists())
    bad=start('mismatch')
    try:
        def rejected():
            log=(out/'host/game.log').read_text(encoding='utf8',errors='ignore').lower()
            return 'client connecting with invalid version' in log or 'incompatible version' in log
        wait(200,rejected)
        (out/'mismatch.json').write_text(json.dumps(dict(older_module_rejected=True)))
    finally:
        if bad.poll() is None:bad.terminate();bad.wait(30)
    peers['client']=start('client')
    wait(600,lambda:(out/'client/accepted.json').exists())
    if peers['client'].wait(60)!=0:raise RuntimeError('client exit')
    peers['rejoin']=start('rejoin')
    wait(480,lambda:(out/'host/finish.json').exists() and (out/'rejoin/rejoined.json').exists())
    for p in peers.values():
        if p.wait(60)!=0:raise RuntimeError('unclean exit')
    initial=[load(out/k/'initial.json') for k in ('host','client')]
    fixed=[load(out/k/'repaired.json') for k in ('host','client')]
    reopened=load(out/'rejoin/rejoined.json')
    ground={k:list(csv.DictReader((out/k/'ground.csv').read_text(encoding='utf-8-sig').splitlines())) for k in peers}
    physical=max(abs(float(v['height_cm'])-float(v['collision_cm'])) for rows in ground.values() for v in rows)
    network=max(abs(float(row['height_cm'])-float(ground['host'][i]['height_cm'])) for rows in ground.values() for i,row in enumerate(rows))
    checks={'older_module_rejected':(out/'mismatch.json').exists(),'ruined_equal':initial[0]==initial[1], 'ruined_gate':all(v['grove']>0 and v['runoff']==v['mill_work_parts']==v['doors']==v['lamps']==v['mill_keeper']==0 for v in initial),
            'repaired_equal':fixed[0]==fixed[1], 'repaired_parts':all(v['runoff']==1 and v['mill_keeper']==v['tavern_keeper']==1 and v['doors']==5 and v['lamps']>0 and v['mill_work_parts']>0 for v in fixed),
            'door_and_dialogue':(out/'client/client-dialogue.txt').is_file() and load(out/'client/accepted.json')['open_doors']==1,
            'late_join_repair_and_door':reopened['mill'] and reopened['inn'] and reopened['open_doors']==1 and reopened['mill_keeper']==1,
            'shared_height':network<.05 and physical<.8,'clean_exit':all(p.returncode==0 for p in peers.values())}
    report=dict(checks=checks,passed=all(checks.values()),points=len(ground['host']),max_collision_error_cm=physical,max_peer_error_cm=network,loss_percent=2,lag_ms=60)
    (out/'result.json').write_text(json.dumps(report,indent=2))
    print(report)
    if not report['passed']:
        raise SystemExit(1)
finally:
    for p in peers.values():
        if p.poll() is None:p.terminate();p.wait(30)
