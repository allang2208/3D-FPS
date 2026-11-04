"""Publish only the saved exclusive option and recipe, preserving shared variants."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;DATA=P.parents[2]/'Content/ColdSteelData'
d=json.loads((P/'design.json').read_text('utf-8'))
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete'] or not saved.get('icon'):raise RuntimeError('Mesh and icon packages are not saved yet')
part=saved['parts'][0]
def update(name,edit):
    p=DATA/name;before=p.read_bytes();data=json.loads(before);edit(data)
    backup=P/'Before'/name
    if not backup.exists():backup.write_bytes(before)
    if p.read_bytes()!=before:raise RuntimeError('Concurrent edit preserved: '+name)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def modules(data):
    spec={k:part[k] for k in ('mesh','location_cm','material_slot_names','trace_base_cm','trace_tip_cm')}
    spec['materials']={k:part['material'] for k in part['material_slot_names']};spec['appearance']=d['appearance']
    data['slots']['blade_1'][d['id']]=spec
def catalog(data):
    options=next(c for c in data['columns'] if c['key']=='blade_1').setdefault('options',[])
    option={k:d[k] for k in ('id','name','appearance','stats','effects','special_effects')};option['description']=d['appearance']
    index=next((i for i,o in enumerate(options) if o['id']==d['id']),None)
    if index is None:options.append(option)
    else:options[index]=option
icon_name='ue_tactical_hatchet_blade_1_hatchet_falcon_edge.png'
shutil.copy2(P/'Icons'/icon_name,DATA/'AttachmentIcons20260913'/icon_name)
update('tactical-hatchet-modules.json',modules);update('tactical-hatchet-gunsmith.json',catalog)
(P/'registration_receipt.json').write_text(json.dumps({'published':True,'definition':d['weapon'],'id':d['id'],
    'name':d['name'],'slot':'blade_1','modification_tier':'Special','stats':d['stats'],'saved_assets':saved['assets'],
    'existing_grip_pommel_lanyard_recipes_retained':True,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FALCON_EDGE_REGISTERED')
