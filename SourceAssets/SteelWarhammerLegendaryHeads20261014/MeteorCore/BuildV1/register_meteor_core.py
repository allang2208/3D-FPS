"""Register only this weapon-exclusive paired head after asset saves complete."""
import json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3];DATA=ROOT/'Content/ColdSteelData'
catalog=runpy.run_path(str(P/'catalog.py'));option=catalog['OPTION'].copy()
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save model, materials and icon before registering')
before=P/'Before';before.mkdir(exist_ok=True)
def read(path):
    if not (before/path.name).exists():shutil.copy2(path,before/path.name)
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-gunsmith.json';gunsmith=read(path)
column=next(c for c in gunsmith['columns'] if c['key']=='hammer_heads')
existing=next((o for o in column['options'] if o['id']==option['id']),None)
if existing:
    for key in ('stats','effects','special_effects'):
        if key in existing:option[key]=existing[key]
    existing.update(option)
else:column['options'].append(option)
write(path,gunsmith)
path=DATA/'warhammer-modules.json';modules=read(path)
row=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'][0]
choice=modules['slots']['hammer_heads'].get(option['id'],{}).copy()
choice.update(mesh=catalog['MESH_DIR']+'/'+row['mesh']+'.'+row['mesh'],location_cm=row['location_cm'],appearance=option['appearance'],
 interface='warhammer_factory_v1',exclusive_weapon='ue_steel_warhammer',model_revision='MeteorCoreV1')
modules['slots']['hammer_heads'][option['id']]=choice;write(path,modules)
(P/'registration_receipt.json').write_text(json.dumps({'id':option['id'],'slot':'hammer_heads','host':'ue_steel_warhammer',
 'tier':'legendary','exclusive':True,'mesh':choice['mesh'],'icon':'ue_steel_warhammer_hammer_heads_meteor_core',
 'stats':option['stats'],'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('METEOR_CORE_REGISTERED',flush=True)
