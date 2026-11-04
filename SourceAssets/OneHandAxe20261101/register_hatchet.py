"""Publish the new catalog entry without replacing unrelated shared catalog text."""
import copy
import json
import shutil
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DATA=ROOT/'Content/ColdSteelData'
path=DATA/'items.json'
raw=path.read_text('utf-8-sig')
items=json.loads(raw)
item=copy.deepcopy(items['ue_kukri'])
asset='/Game/Weapons/TacticalHatchet20261101/SM_TacticalHatchet.SM_TacticalHatchet'
item.update(id='ue_tactical_hatchet',name='碳钢战斧',type='单手斧',weaponType='hatchet',
    weaponTypeTag='单手近战武器',melee_animation_family='kukri',modular_melee_catalog='tactical-hatchet-modules.json',
    grid_w=2,grid_h=3,ue_icon='Icons/ue_tactical_hatchet.png',icon_fallback='单手斧',
    melee_damage=40,attack_seconds=1.05,melee_stamina=10,
    world_mesh=asset,offhand_melee_mesh=asset,
    desc='深灰碳钢斧面衔接银色磨刃，短斧背与通长金属柄骨连成紧凑轮廓。黑色防滑握片包覆握持区，弧形柄尾收住掌根。可作为主手或副手单手近战武器使用。')
if item['id'] in items:
    raise RuntimeError('Hatchet already registered; edit its exact fields instead of re-running publication')
needle='"ue_kukri":'
start=raw.index('{',raw.index(needle))
_,count=json.JSONDecoder().raw_decode(raw[start:])
chunk=raw[start:start+count]
old='"weaponTypeTag": '+json.dumps(items['ue_kukri']['weaponTypeTag'],ensure_ascii=False)
new='"weaponTypeTag": "单手近战武器"'
if old not in chunk: raise RuntimeError('Existing kukri tag changed')
raw=raw[:start]+chunk.replace(old,new,1)+raw[start+count:]
entry=json.dumps(item,ensure_ascii=False,indent=2)
entry='  "ue_tactical_hatchet": '+entry.replace('\n','\n  ')
raw=raw.rstrip()[:-1].rstrip()+',\n'+entry+'\n}\n'
path.write_text(raw,encoding='utf-8')
model=json.loads((P/'model.json').read_text('utf-8'))
catalog=dict(version=1,interface='kukri-grip-frame-v1-20261026',root_slot='blade_1',module_slots=['blade_1'],
    arms_mesh=item['viewmodel_mesh'],bone_mount=dict(rotation_xyzw=[0,0,0,1],location_cm=[0,0,0],scale=[.01,.01,.01]),
    slots={'blade_1':{'factory':dict(mesh=asset,location_cm=[0,0,0],appearance='碳钢斧体与防滑握片，保留原装完整外形。',
        trace_base_cm=model['trace_base_cm'],trace_tip_cm=model['trace_tip_cm'],
        material_slot_names=['M_TacticalHatchet'],materials={'M_TacticalHatchet':'/Game/Weapons/TacticalHatchet20261101/Materials/M_TacticalHatchet.M_TacticalHatchet'})}})
gunsmith=dict(version=1,weapon=item['id'],columns=[dict(key='blade_1',name='斧体',default='原装斧体',
    description='深灰碳钢斧面、银色磨刃与黑色防滑握片。',options=[])])
for name,data in [('tactical-hatchet-modules.json',catalog),('tactical-hatchet-gunsmith.json',gunsmith)]:
    (DATA/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(P/'Icons/ue_tactical_hatchet.png',DATA/'Icons/ue_tactical_hatchet.png')
source=ROOT/'Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp'
text=source.read_text('utf-8-sig')
old='TEXT("ue_thunder_god_hammer"), TEXT("ue_kukri")})'
if old not in text: raise RuntimeError('Armory list changed')
source.write_text(text.replace(old,'TEXT("ue_thunder_god_hammer"), TEXT("ue_kukri"), TEXT("ue_tactical_hatchet")})',1),encoding='utf-8')
print('Registered ue_tactical_hatchet; shared kukri moveset; own model/catalog/icon; starting armory entry.')
