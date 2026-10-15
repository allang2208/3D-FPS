"""Publish the saved paired head under the existing shared hammer-head slot."""
import json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3];DATA=ROOT/'Content/ColdSteelData'
catalog=runpy.run_path(str(P/'catalog.py'));option=catalog['OPTION'].copy()
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save mesh and icon before publishing this option')
before=P/'Before';before.mkdir(exist_ok=True)
def read(path):
    if not (before/path.name).exists():shutil.copy2(path,before/path.name)
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
library=DATA/'common-hammer-heads.json';shared=read(library)
existing=next((o for o in shared['options'] if o['id']==option['id']),None)
if existing:
    # A later appearance refresh must not erase separately assigned balance values.
    for key in ('stats','effects','special_effects'):
        if key in existing:option[key]=existing[key]
    existing.update(option)
else:shared['options'].append(option)
write(library,shared)
path=DATA/'warhammer-modules.json';modules=read(path)
row=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'][0]
choice=modules['slots']['hammer_heads'].get(option['id'],{}).copy()
choice.update(mesh=catalog['MESH_DIR']+'/'+row['mesh']+'.'+row['mesh'],location_cm=row['location_cm'],
 appearance=option['appearance'],interface='warhammer_factory_v1',shared_option_library=library.name,model_revision='PointedHammerV1')
modules['slots']['hammer_heads'][option['id']]=choice;write(path,modules)
(P/'registration_receipt.json').write_text(json.dumps({'id':option['id'],'slot':'hammer_heads','library':library.name,
 'host':'ue_steel_warhammer','tier':'special','mesh':choice['mesh'],'runtime_icon':'hammer_heads_pointed_hammer',
 'stats':option['stats'],'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('POINTED_HAMMER_REGISTERED',flush=True)
