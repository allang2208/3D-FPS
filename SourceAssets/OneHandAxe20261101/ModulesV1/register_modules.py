"""Publish only this weapon's catalogs after the actual assets have been saved."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=P.parents[2]/'Content/ColdSteelData'
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Module assets have not finished saving')
path=DATA/'tactical-hatchet-modules.json'
catalog=json.loads(path.read_text(encoding='utf-8'))
old_head=catalog['slots']['blade_1']['factory']
descriptions={'blade_1':'深灰碳钢斧头与一体斧颈，保留银色磨刃及原有攻击轮廓。',
    'grip':'黑色防滑握片包覆原装柄骨，保留铆钉与既有握持尺寸。',
    'pommel':'弧形原装柄尾衔接掌根，保留穿绳孔。'}
shared=json.loads((DATA/'shared-knife-component-options.json').read_text(encoding='utf-8'))
appearance={o['id']:o['appearance'] for c in shared['columns'] for o in c['options']}
catalog['module_slots']=list(dict.fromkeys(['blade_1','grip','pommel']+catalog.get('module_slots',[])))
catalog['part_interface']='hatchet-factory-cuts-v1'
# Keep later recipes and attachment slots when rebuilding the original batch.
catalog.setdefault('slots',{})
for slot in catalog['module_slots']:catalog['slots'].setdefault(slot,{})
for e in receipt['parts']:
    spec={k:e[k] for k in ('mesh','location_cm','material_slot_names')}
    spec['materials']={name:e['material'] for name in e['material_slot_names']}
    spec['appearance']=descriptions[e['slot']] if e['id']=='factory' else appearance[e['id']]
    if e['slot']=='blade_1':
        for key in ('trace_base_cm','trace_tip_cm'):spec[key]=old_head[key]
        if e['id']=='factory' and old_head.get('rune_carrier_source_mesh')==e['mesh']:
            for key in ('mesh','material_slot_names','materials','rune_carrier_source_mesh','rune_surface_revision'):
                if key in old_head:spec[key]=old_head[key]
    catalog['slots'][e['slot']][e['id']]=spec
gunsmith_path=DATA/'tactical-hatchet-gunsmith.json'
gunsmith=json.loads(gunsmith_path.read_text(encoding='utf-8')) if gunsmith_path.exists() else {'version':1,'weapon':'ue_tactical_hatchet','columns':[]}
for slot,label,default in [('blade_1','斧头','原装斧头'),('grip','握柄','原装握柄'),('pommel','柄尾','原装柄尾')]:
    column=next((c for c in gunsmith['columns'] if c['key']==slot),None)
    if column is None:
        column={'key':slot,'options':[]};gunsmith['columns'].append(column)
    column.update(name=label,default=default,description=descriptions[slot])
    if slot!='blade_1':column.update(options_library='shared-knife-component-options.json',options_column=slot)
for name,data in [('tactical-hatchet-modules.json',catalog),('tactical-hatchet-gunsmith.json',gunsmith)]:
    target=DATA/name;before=P/'Before'/name
    if not before.exists():shutil.copy2(target,before)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'registration_receipt.json').write_text(json.dumps({'published':True,'factory_slots':3,'shared_grip_options':3,'shared_pommel_options':3,
    'item_id':'ue_tactical_hatchet','stats_changed':False,'shared_icons_duplicated':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('HATCHET_MODULES_REGISTERED')
