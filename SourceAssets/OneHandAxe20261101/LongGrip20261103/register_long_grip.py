"""Append one axe-only option after its mesh/PBR/icon assets have been saved."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;DATA=P.parents[2]/'Content/ColdSteelData'
entry=json.loads((P/'long_grip.json').read_text('utf-8'))
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete'] or not saved.get('icon'):raise RuntimeError('Long grip assets have not finished saving')
part=saved['parts'][0]
appearance='加长碳钢芯骨衔接黑色棱纹握片，两道窄金属带环绕下段，保留原装上下接面。'
option={'id':entry['id'],'name':'长柄握把','description':appearance,'appearance':appearance,
        'stats':entry['stats'],
        'effects':[{'text':'攻击距离+25%','benefit':1},{'text':'物理攻击+10%','benefit':1},
                   {'text':'体力消耗+10%','benefit':-1},{'text':'攻击速度-5%','benefit':-1}],
        'special_effects':[]}
def update(name,edit):
    path=DATA/name;original=path.read_bytes();data=json.loads(original)
    edit(data)
    before=P/'Before'/name
    if not before.exists():before.write_bytes(original)
    if path.read_bytes()!=original:raise RuntimeError('Concurrent catalog edit preserved: '+name)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def modules(data):
    spec={k:part[k] for k in ['mesh','location_cm','pommel_offset_cm','material_slot_names']}
    spec['materials']={name:part['material'] for name in part['material_slot_names']}
    spec['appearance']=appearance
    data['slots']['grip'][entry['id']]=spec
def gunsmith(data):
    column=next(c for c in data['columns'] if c['key']=='grip')
    options=column.setdefault('options',[])
    index=next((i for i,o in enumerate(options) if o['id']==entry['id']),None)
    if index is None:options.append(option)
    else:options[index]=option
update('tactical-hatchet-modules.json',modules)
update('tactical-hatchet-gunsmith.json',gunsmith)
receipt={'published':True,'definition':'ue_tactical_hatchet','slot':'grip','id':entry['id'],
         'exclusive_option':True,'stats':entry['stats'],'pommel_offset_cm':entry['pommel_offset_cm'],
         'pendant_follows_parent_pommel':True,'saved_assets':saved['assets'],'runtime_tested':False}
(P/'registration_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('HATCHET_LONG_GRIP_REGISTERED')
