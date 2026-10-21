"""Publish only the three normal attacks and their existing recovery aliases."""
import hashlib
import json
import re
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
saved=json.loads((OUT/'assets-saved.json').read_text())
commandlet=json.loads((OUT.parent/'save_natural_combo_v17-commandlet.json').read_text(encoding='utf-8-sig'))
if not saved.get('complete') or len(saved['clips'])!=3 or commandlet['exit_code']!=0:
    raise RuntimeError('Finish the three independent animation saves first.')
build=json.loads((OUT/'completed-build.json').read_text());binary=Path(build['binary'])
if build['status']!='Succeeded' or binary.stat().st_mtime<build['binary_mtime']:
    raise RuntimeError('Complete the matching Editor build first.')
for name,entry in build['sources'].items():
    path=Path(name)
    if path.stat().st_mtime>binary.stat().st_mtime or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise RuntimeError('Source changed after the recorded build: '+name)
previous=json.loads((OUT.parent/'RefinementV8/assets-published.json').read_text())['clips']
roles={};old={}
for label in ('Slash1','Slash2','Slash3'):
    for suffix in ('','Recover'):
        key='Warhammer.FullBody.'+label+suffix
        roles[key]=saved['clips']['Warhammer.FullBody.'+label];old[key]=previous[key]
path=ROOT/'Content/ColdSteelData/player_body.json'
before_bytes=path.read_bytes();text=before_bytes.decode('utf-8-sig');cfg=json.loads(text)
for key,value in roles.items():
    if cfg['clips'].get(key)!=old[key]:raise RuntimeError('Attack reference changed: '+key)
    pattern=r'('+re.escape(json.dumps(key))+r'\s*:\s*)'+re.escape(json.dumps(old[key]))
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(value),text)
    if count!=1:raise RuntimeError('Expected one configuration entry: '+key)
config_write=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before_bytes,text,owned_paths=[('clips',key) for key in roles],producer=__file__)
saved['config_write']=config_write
saved.update(published=True,clips=roles,previous=old,build=build,runtime_tested=False)
(OUT/'assets-published.json').write_text(json.dumps(saved,indent=2))
print('HAMMER_NATURAL_COMBO_PUBLISHED 6 roles / 3 source takes')
