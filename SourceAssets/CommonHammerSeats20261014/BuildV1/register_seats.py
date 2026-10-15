"""Merge this slot only, after its meshes, materials and icons have been saved."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
options=runpy.run_path(str(P/'catalog.py'))['OPTIONS']
library=DATA/'common-hammer-seats.json'
existing=json.loads(library.read_text(encoding='utf-8-sig')) if library.exists() else {'version':1,'slot':'head_mount','options':[]}
incoming={o['id']:o for o in options}
merged=[]
for old in existing['options']:
    option=incoming.pop(old['id'],None)
    if option:
        # A geometry refresh cannot erase subsequently authored numerical balance.
        for key in ('stats','effects','special_effects'):
            if old.get(key):option[key]=old[key]
        merged.append(option)
    else:merged.append(old)
existing['options']=merged+list(incoming.values())
library.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-gunsmith.json';root=json.loads(path.read_text(encoding='utf-8-sig'))
next(c for c in root['columns'] if c['key']=='head_mount')['options_library']=library.name
path.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-modules.json';root=json.loads(path.read_text(encoding='utf-8-sig'))
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
for row in rows:
    option=next(o for o in options if o['id']==row['id']);package='/Game/Weapons/CommonHammerSeats20261014/BuildV1/'+row['mesh']
    root['slots']['head_mount'][row['id']]={'mesh':package+'.'+row['mesh'],'location_cm':[0,0,0],
        'appearance':option['appearance'],'interface':'warhammer_factory_v1','shared_option_library':library.name,'model_revision':'BuildV1'}
path.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMMON_HAMMER_SEATS_REGISTERED '+','.join(o['id'] for o in options))
