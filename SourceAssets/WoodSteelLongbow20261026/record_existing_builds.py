"""Attach completed shared builds to this weapon delivery without rebuilding loaded binaries."""
from pathlib import Path
import json,hashlib,datetime
P=Path(__file__).parent;project=P.parents[1]
src=project/'Source/FPSGAME'
sources=[src/'Weapons/Bow'/name for name in ['BowArmsMeshComponent.h','BowArmsMeshComponent.cpp','BowGunsmith.cpp','BowWeaponComponent.cpp']]+[src/'UI/M4GunsmithLayout.cpp']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
for target,platform,binary,stamp in [
    ('FPSGAMEEditor','UnrealEditor','UnrealEditor-FPSGAME.dll','143244'),
    ('FPSGAME','UnrealGame','FPSGAME.exe','142737')]:
    log=project/'Saved/PerformanceNext20261026'/(target+'-20261026-'+stamp+'.log')
    result=log.read_text(encoding='utf-8-sig',errors='replace')
    if 'Result: Succeeded' not in result:raise RuntimeError('Shared build did not succeed: '+str(log))
    binary_path=project/'Binaries/Win64'/binary
    objects=[]
    for source in sources:
        if source.suffix!='.cpp':continue
        obj=project/'Intermediate/Build/Win64/x64'/platform/'Development/FPSGAME'/(source.name+'.obj')
        newest=source.stat().st_mtime
        if source.name in ['BowArmsMeshComponent.cpp','BowWeaponComponent.cpp']:
            newest=max(newest,sources[0].stat().st_mtime)
        if obj.stat().st_mtime<newest or binary_path.stat().st_mtime<obj.stat().st_mtime:
            raise RuntimeError('Source or object changed after the selected build: '+str(source))
        objects.append(str(obj))
    receipt={'target':target,'exit_code':0,'mode':'reused_completed_shared_build','log':str(log),
        'binary':str(binary_path),'objects':objects,'source_sha256':hashes,
        'recorded':datetime.datetime.now().isoformat(),'game_run':False,'gameplay_tested':False}
    (P/('build-'+target+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('LONGBOW_EXISTING_EDITOR_AND_GAME_BUILDS_RECORDED')
