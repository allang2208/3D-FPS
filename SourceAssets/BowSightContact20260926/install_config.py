"""Activate only after this batch's assets are saved. Preserve current shared fields."""
import json
from pathlib import Path
P=Path(__file__).parent;ROOT=Path('D:/FPS3D/FPSGAME')
r=json.loads((P/'import-receipt.json').read_text())
expected=['A_Bow_'+n for n in ['Idle','Ready','Equip','Nock','Draw','Hold','Release','Run']]+['SM_Bow_OpenMechanicalSight']
if any(n not in r['saved'] for n in expected):raise RuntimeError('Incomplete import; catalog not changed')
path=ROOT/'Content/ColdSteelData/bows.json';d=json.loads(path.read_text(encoding='utf-8-sig'));bow=d['bow_dark']
bow.update({'bow_animation_prefix':'/Game/Weapons/DarkBow20260925/SightContactV11/A_Bow_',
    'bow_part_sight_mesh':r['saved']['SM_Bow_OpenMechanicalSight'],'bow_part_sight_rods':0,
    'bow_part_sight_scale':1.,'bow_part_sight_location_cm':'0,0,0','bow_part_sight_rotation_deg':'0,0,0',
    'bow_ads_sight_cm':'-3.5,-13.9,14.6','bow_ads_sight_distance_cm':78.,'bow_presentation_revision':22})
slots=bow['bow_part_slots'].split(',')
if 'sight' not in slots:slots.append('sight')
bow['bow_part_slots']=','.join(slots)
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
ini=ROOT/'Config/DefaultGame.ini';s=ini.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/SightContactV11")'
if line not in s:
    anchor='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/ReferenceUpgradeV10")'
    if anchor not in s:raise RuntimeError('Cook section anchor missing')
    ini.write_text(s.replace(anchor,anchor+'\n'+line),encoding='utf8')
print('BOW_SIGHT_V11_CONFIG_ACTIVATED revision=22')
