from pathlib import Path
import hashlib,json,re
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
files=[R/'Content/ColdSteelData/thunder-god-hammer-modules.json',R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json']
prod=R/'Source/FPSGAME/Production'
files.extend([prod/'ProductionToolComponent.cpp',prod/'ProductionStormDriveLightning.cpp'])
for pattern in ('ThunderHammer*.*','ProductionThunder*.cpp','ProductionBlunt*.cpp','Warhammer*.*'):
    files.extend(prod.glob(pattern))
paths={}
# JiLei's shared lightning renderer resolves this symbol from another hammer.
shared=prod/'RuneboundHammerTuning.h'
lightning=re.search(r'FinalTollLightning=TEXT\("([^"]+)"\)',shared.read_text(encoding='utf-8-sig')).group(1)
paths[lightning.split('.')[0]]=[str(shared.relative_to(R))+':FinalTollLightning (shared StormDrive renderer)']
catalog=R/'Content/ColdSteelData/items.json'
hammer=json.loads(catalog.read_text(encoding='utf-8-sig'))['ue_thunder_god_hammer']
for key in ('tool_mesh','world_mesh','tool_viewmodel','viewmodel_mesh','tool_swing_sound','tool_sound','hit_sound'):
    value=hammer.get(key,'')
    if value.startswith('/Game/'):paths.setdefault(value.split('.')[0],[]).append('Content/ColdSteelData/items.json:'+key)
for clip in ('Idle','Equip','Swing','HitRecover'):
    paths.setdefault(hammer['tool_animation_prefix']+clip,[]).append('Content/ColdSteelData/items.json:tool_animation_prefix')
for f in files:
    for path in re.findall(r'/Game/[A-Za-z0-9_/.]+',f.read_text(encoding='utf-8-sig')):
        package=path.split('.')[0]
        # Directory constants and generated filename prefixes are not asset references.
        disk=R/'Content'/package.removeprefix('/Game/')
        if disk.is_dir() or path.endswith(('/','_')):continue
        paths.setdefault(package,[]).append(str(f.relative_to(R)))
rows=[]
for package,refs in sorted(paths.items()):
    p=R/'Content'/(package.removeprefix('/Game/')+'.uasset')
    rows.append(dict(package=package,exists=p.is_file(),bytes=p.stat().st_size if p.exists() else 0,sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,consumers=sorted(set(refs))))
config=(R/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
cook=re.findall(r'DirectoriesToAlwaysCook=\(Path="([^"]+)"',config)
for row in rows:row['explicit_cook_root']=next((x for x in cook if row['package'].startswith(x+'/')),None)
out=dict(passed=all(x['exists'] for x in rows),scope='literal asset references, current module table and catalog-derived motion references; file existence and cook roots, not runtime proof',assets=rows)
(O/'dependency-preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('literal packages',len(rows),'missing',[x['package'] for x in rows if not x['exists']])
print('not explicitly directory-cooked',[x['package'] for x in rows if not x['explicit_cook_root']])
