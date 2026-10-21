"""Replace only the third cut and its recovery after its package is saved."""
import json
import re
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
saved=json.loads((OUT/'assets-saved.json').read_text())
commandlet=json.loads((OUT.parent/'save_slash3_alignment_v18-commandlet.json').read_text(encoding='utf-8-sig'))
if not saved.get('complete') or len(saved['clips'])!=1 or commandlet['exit_code']!=0:
    raise RuntimeError('Complete the independent third-cut save first.')
previous=json.loads((OUT.parent/'NaturalComboV17/assets-published.json').read_text())['clips']
asset=saved['clips']['Warhammer.FullBody.Slash3']
roles={key:asset for key in ('Warhammer.FullBody.Slash3','Warhammer.FullBody.Slash3Recover')}
path=ROOT/'Content/ColdSteelData/player_body.json'
before_bytes=path.read_bytes();text=before_bytes.decode('utf-8-sig');cfg=json.loads(text);old={}
for key,value in roles.items():
    old[key]=previous[key]
    if cfg['clips'].get(key)!=old[key]:raise RuntimeError('Third-cut reference changed: '+key)
    pattern=r'('+re.escape(json.dumps(key))+r'\s*:\s*)'+re.escape(json.dumps(old[key]))
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(value),text)
    if count!=1:raise RuntimeError('Expected one configuration entry: '+key)
config_write=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before_bytes,text,owned_paths=[('clips',key) for key in roles],producer=__file__)
saved['config_write']=config_write
saved.update(published=True,clips=roles,previous=old,runtime_code_changed=False,runtime_tested=False)
(OUT/'assets-published.json').write_text(json.dumps(saved,indent=2))
print('HAMMER_SLASH3_ALIGNMENT_PUBLISHED 2 roles / 1 source take')
