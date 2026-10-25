"""Reverse the accepted entry trajectories, then hold the standing handoff."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/HangingEntryV6'
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ReversedExitV7'
OUT.mkdir(parents=True,exist_ok=True)
source=json.loads((BASE/'authored.json').read_text());result=copy.deepcopy(source)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,ix,bind=[ns[k] for k in ('fk','ix','bind')]
configs={name:json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig'))
         for name in ('furniture_rest.json','apartment_furniture_rest.json')}
changed=[];timing={}
for role,take in source['clips'].items():
    if not role.endswith('.Enter'):continue
    kind=role.split('.')[1];exit_role='Rest.'+kind+'.Exit'
    frames=copy.deepcopy(take['frames'][::-1])
    hold_frames=round(.3*take['rate'])
    frames.extend(copy.deepcopy(frames[-1]) for _ in range(hold_frames))
    duration=(len(frames)-1)/take['rate']
    result['clips'][exit_role]={'rate':take['rate'],'duration':duration,'frames':frames}
    camera=[]
    for frame in frames:
        w=fk(np.array(frame));head=w[ix['head']]
        eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
        camera.append([*eye.tolist(),0.,0.])
    config=configs['apartment_furniture_rest.json' if kind.startswith('Apartment') else 'furniture_rest.json']
    config['clips'][exit_role]={'duration':duration,'camera':camera}
    changed.append(exit_role)
    timing[kind]={'reverse_seconds':take['duration'],'standing_hold_seconds':hold_frames/take['rate'],'exit_duration':duration}
    print('REVERSED_EXIT_AUTHORED',exit_role,len(frames),flush=True)
result['changed_roles']=changed
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
for name,config in configs.items():(OUT/name).write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
merged=copy.deepcopy(configs['furniture_rest.json'])
for key in ('clips','types'):merged[key].update(configs['apartment_furniture_rest.json'][key])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture']
(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True)
(OUT/'Geometry/index.json').write_bytes((BASE/'Geometry/index.json').read_bytes())
(OUT/'source_revision.json').write_text(json.dumps({'base':str(BASE/'authored.json'),
    'base_sha256':hashlib.sha256((BASE/'authored.json').read_bytes()).hexdigest(),
    'changed_roles':changed,'entry_and_idle_reused':True,'timing':timing},indent=2))
