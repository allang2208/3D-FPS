"""Connect only the successfully saved fitted Sparrow clips to the body library."""
import hashlib,json,runpy
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1]
r=json.loads((O/'assets-saved.json').read_text())
if not r['complete'] or r['authoring_sha256']!=hashlib.sha256((O/'authored.json.gz').read_bytes()).hexdigest():
 raise RuntimeError('The current authored set has not been saved completely')
for path in r['clips'].values():
 if '/AnimationsV3/' not in path:raise RuntimeError('Do not publish a superseded candidate')
 if not (ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file():raise RuntimeError('Missing saved package '+path)
p=ROOT/'Content/ColdSteelData/player_body.json';before_bytes=p.read_bytes();cfg=json.loads(before_bytes.decode('utf-8-sig'))
before={k:cfg['clips'].get(k) for k in r['clips']};cfg['clips'].update(r['clips'])
runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
 p,before_bytes,cfg,owned_paths=[('clips',key) for key in r['clips']],producer=__file__)
(O/'published.json').write_text(json.dumps({'before':before,'clips':r['clips'],'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'game_run':False},indent=2))
print('SPARROW_BOW_LIBRARY_PUBLISHED',len(r['clips']))
