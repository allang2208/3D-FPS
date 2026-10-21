"""Publish the separated-grip carry family after saving and building moving-attack leg blending."""
import json
import re
import runpy
import hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
receipt=json.loads((OUT/'assets-saved.json').read_text())
commandlet=json.loads((OUT.parent/'save_source_grip_v16-commandlet.json').read_text(encoding='utf-8-sig'))
if not receipt.get('complete') or len(receipt['clips'])!=9 or commandlet['exit_code']!=0:
    raise RuntimeError('Complete the nine source-carry asset saves first.')
if not (OUT/'build-editor.log').exists() or 'Editor modules built.' not in (OUT/'build-editor.log').read_text(encoding='utf-8-sig',errors='replace'):
    completed=json.loads((OUT/'completed-build.json').read_text())
    source=Path(completed['source']);binary=Path(completed['binary'])
    if completed['status']!='Succeeded' or hashlib.sha256(source.read_bytes()).hexdigest()!=completed['source_sha256']:
        raise RuntimeError('Build current moving normal-attack leg blending before publishing.')
    if source.stat().st_mtime>binary.stat().st_mtime or binary.stat().st_mtime<completed['binary_mtime']:
        raise RuntimeError('The source-carry binary is stale.')
    receipt['completed_build']=completed
old=json.loads((OUT.parent/'SourceCarryV15/assets-published.json').read_text())['clips']
idle=receipt['clips']['Warhammer.FullBody.Idle']
roles={'Warhammer.Idle':idle,'Warhammer.FullBody.Carry':idle,'Warhammer.FullBody.SprintCarry':idle}
for direction in ('Fwd','Fwd_Right','Right','Bwd_Right','Bwd','Bwd_Left','Left','Fwd_Left'):
    for pace in ('Walk','Jog'):
        roles['Warhammer.'+pace+'.'+direction]=receipt['clips']['Warhammer.FullBody.Gait_'+direction]
path=ROOT/'Content/ColdSteelData/player_body.json'
before_bytes=path.read_bytes();text=before_bytes.decode('utf-8-sig');cfg=json.loads(text)
for key,value in roles.items():
    if cfg['clips'].get(key)!=old[key]:raise RuntimeError('Carry reference changed: '+key)
    pattern=r'('+re.escape(json.dumps(key))+r'\s*:\s*)'+re.escape(json.dumps(old[key]))
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(value),text)
    if count!=1:raise RuntimeError('Expected one configuration entry: '+key)
config_write=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before_bytes,text,owned_paths=[('clips',key) for key in roles],producer=__file__)
receipt['config_write']=config_write
receipt.update(published=True,clips=roles,previous=old,runtime_tested=False)
(OUT/'assets-published.json').write_text(json.dumps(receipt,indent=2))
print('HAMMER_SOURCE_GRIP_V16_PUBLISHED 19 roles / 9 shared source assets')
