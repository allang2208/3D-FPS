"""Activate the saved wooden sight and a continuous, slightly closer ADS pose."""
import json
from pathlib import Path
P=Path(__file__).parent;ROOT=Path('D:/FPS3D/FPSGAME')
r=json.loads((P/'import-receipt.json').read_text())
name='SM_Bow_CarvedWoodSight'
if name not in r['saved']:raise RuntimeError('Import/save must complete before activation')
path=ROOT/'Content/ColdSteelData/bows.json';d=json.loads(path.read_text(encoding='utf-8-sig'))
bow=d['bow_dark'];pin=r['sight_pin_cm']
bow.update({'bow_part_sight_mesh':r['saved'][name],'bow_part_sight_rods':0,
    'bow_part_sight_scale':1.,'bow_part_sight_location_cm':'0,0,0','bow_part_sight_rotation_deg':'0,0,0',
    'bow_ads_sight_cm':','.join(f'{x:g}' for x in pin),'bow_ads_sight_distance_cm':75.,
    'bow_ads_in_seconds':.24,'bow_ads_out_seconds':.20,'bow_presentation_revision':23})
slots=bow['bow_part_slots'].split(',')
if 'sight' not in slots:slots.append('sight')
bow['bow_part_slots']=','.join(slots)
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
ini=ROOT/'Config/DefaultGame.ini';s=ini.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/WoodSightV12")'
if line not in s:
    anchor='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/SightContactV11")'
    if anchor not in s:raise RuntimeError('Cook section anchor missing')
    ini.write_text(s.replace(anchor,anchor+'\n'+line),encoding='utf8')
print('BOW_WOOD_SIGHT_CONFIG_ACTIVATED revision=23 ADS=75cm in=.24 out=.20')
