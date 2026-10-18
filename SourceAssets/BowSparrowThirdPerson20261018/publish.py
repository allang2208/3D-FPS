"""Connect only the successfully saved fitted Sparrow clips to the body library."""
import hashlib,json
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1]
r=json.loads((O/'assets-saved.json').read_text())
if not r['complete'] or r['authoring_sha256']!=hashlib.sha256((O/'authored.json.gz').read_bytes()).hexdigest():
 raise RuntimeError('The current authored set has not been saved completely')
for path in r['clips'].values():
 if '/AnimationsV3/' not in path:raise RuntimeError('Do not publish a superseded candidate')
 if not (ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file():raise RuntimeError('Missing saved package '+path)
p=ROOT/'Content/ColdSteelData/player_body.json';cfg=json.loads(p.read_text(encoding='utf-8-sig'))
before={k:cfg['clips'].get(k) for k in r['clips']};cfg['clips'].update(r['clips'])
temp=p.with_name('player_body.bow-sparrow.tmp');temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(p)
(O/'published.json').write_text(json.dumps({'before':before,'clips':r['clips'],'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'game_run':False},indent=2))
print('SPARROW_BOW_LIBRARY_PUBLISHED',len(r['clips']))
