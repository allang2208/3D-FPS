"""Merge only the three shared head options; preserve other slots and authors' work."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
options=runpy.run_path(str(P/'catalog.py'))['OPTIONS']
library=DATA/'common-hammer-heads.json'
previous=json.loads(library.read_text(encoding='utf-8-sig')) if library.exists() else {'version':1,'slot':'hammer_heads','options':[]}
updated={o['id']:o for o in options}
previous['options']=[updated.pop(o['id'],o) for o in previous['options']]+list(updated.values())
library.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-gunsmith.json';root=json.loads(path.read_text(encoding='utf-8-sig'))
next(column for column in root['columns'] if column['key']=='hammer_heads')['options_library']=library.name
path.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'];path=DATA/'warhammer-modules.json';root=json.loads(path.read_text(encoding='utf-8-sig'))
for row in rows:
    option=next(o for o in options if o['id']==row['id']);package='/Game/Weapons/CommonHammerHeads20261014/'+row['mesh']
    choice=root['slots']['hammer_heads'].get(row['id'],{}).copy()
    # A stat/copy refresh must retain the currently installed model revision.
    choice.setdefault('mesh',package+'.'+row['mesh']);choice.setdefault('location_cm',row['location_cm'])
    choice.update(appearance=option['appearance'],interface='warhammer_factory_v1',shared_option_library=library.name)
    root['slots']['hammer_heads'][row['id']]=choice
path.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMMON_HAMMER_HEADS_REGISTERED',','.join(o['id'] for o in options))
