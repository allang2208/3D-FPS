"""Switch the existing grip ID to its saved hollow geometry, retaining all stats."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;DATA=P.parents[3]/'Content/ColdSteelData'
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete'] or not saved.get('icon'):raise RuntimeError('Hollow grip assets are not saved yet')
part=saved['parts'][0]
appearance='长圆贯穿孔夹在连续金属侧框之间，银灰孔缘衔接黑色碳纤维握片，两端保留原装连接座与紧固件。'
def update(path,edit):
    original=path.read_bytes();data=json.loads(original);edit(data)
    backup=P/'Before'/path.name
    if not backup.exists():backup.write_bytes(original)
    if path.read_bytes()!=original:raise RuntimeError('Concurrent edit preserved: '+str(path))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def modules(data):
    spec={k:part[k] for k in ('mesh','location_cm','pommel_offset_cm','material_slot_names')}
    spec['materials']={name:part['material'] for name in part['material_slot_names']};spec['appearance']=appearance
    data['slots']['grip']['hatchet_grip_agile']=spec
def catalog(data):
    option=next(o for c in data['columns'] if c['key']=='grip' for o in c['options'] if o['id']=='hatchet_grip_agile')
    option.update(description=appearance,appearance=appearance)
def design(data):data.update(appearance=appearance,model_revision='hollow_v2_20261103')
def manifest(data):
    data.clear();data.update(json.loads((P/'hollow_grip.json').read_text('utf-8')))
icon_name='ue_tactical_hatchet_grip_hatchet_grip_agile.png'
shutil.copy2(P/'Icons'/icon_name,DATA/'AttachmentIcons20260913'/icon_name)
update(DATA/'tactical-hatchet-modules.json',modules)
update(DATA/'tactical-hatchet-gunsmith.json',catalog)
update(P.parent/'design.json',design)
update(P.parent/'agile_grip.json',manifest)
current=json.loads((P.parent/'design.json').read_text('utf-8'))
(P/'registration_receipt.json').write_text(json.dumps({'published':True,'definition':'ue_tactical_hatchet',
    'slot':'grip','id':'hatchet_grip_agile','name':current['name'],'model_revision':'hollow_v2_20261103',
    'stats_unchanged':True,'stats':current['stats'],'existing_id_and_tier_retained':True,
    'saved_assets':saved['assets'],'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HOLLOW_GRIP_REGISTERED')
