"""Publish only the new grip choices after all referenced assets have been saved."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
catalog=runpy.run_path(str(P/'catalog.py'));options=catalog['OPTIONS'];mesh_dir=catalog['MESH_DIR']
library=DATA/'common-hammer-grips.json'
data=json.loads(library.read_text(encoding='utf-8-sig')) if library.exists() else {'version':1,'slot':'grip','options':[]}
incoming={o['id']:o for o in options};merged=[]
for old in data['options']:
    option=incoming.pop(old['id'],None)
    if option:
        for key in ('stats','effects','special_effects'):
            if old.get(key):option[key]=old[key]
        merged.append(option)
    else:merged.append(old)
data['options']=merged+list(incoming.values());library.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
next(c for c in data['columns'] if c['key']=='grip')['options_library']=library.name
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-modules.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
for row in json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']:
    option=next(o for o in options if o['id']==row['id']);package=mesh_dir+'/'+row['mesh']
    data['slots']['grip'][row['id']]={'mesh':package+'.'+row['mesh'],'location_cm':row['location_cm'],
        'appearance':option['appearance'],'interface':'warhammer_factory_v1','shared_option_library':library.name,'model_revision':'BuildV1/UV1'}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMMON_HAMMER_GRIPS_REGISTERED')
