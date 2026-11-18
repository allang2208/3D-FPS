"""Author the expanded settlement and regenerate its production road/exclusion data."""
import json, runpy, sys, shutil
from pathlib import Path

root=Path(__file__).resolve().parents[3]
source=root/'SourceAssets/TemperateHillsVillage'
out=root/'SourceAssets/HillsVillageBlacksmith20261117'
plan=json.loads((source/'layout.json').read_text(encoding='utf-8'))
plan['surface_extent_m']=[65,50]
plan['houses'][0][1]='村口铁匠铺（待修复）'
for house in [
    ['08','北侧残破民居','SL_Packed_House_TypeA_00B',-11,-39,180],
    ['09','南侧残破长屋','SL_Packed_HouseTypeB_01A',10,39,0]]:
    if not any(h[0]==house[0] for h in plan['houses']):plan['houses'].append(house)
new_roads=[
    dict(name='西门连接路',width=4.2,points=[[-65,0],[-46,0]]),
    dict(name='东门连接路',width=4.2,points=[[46,5],[65,5]]),
    dict(name='北侧居住支路',width=2.2,points=[[-6,-34],[-6,-26],[-7,-20],[-7.5,-17],[-7.5,-13.4]]),
    dict(name='南侧居住支路',width=2.2,points=[[7,26],[8,30],[8,33]])]
for road in new_roads:
    if not any(r['name']==road['name'] for r in plan['roads']):plan['roads'].append(road)
blacksmith_defaults={'house':'01','default_state':'ruined','station_id':'casting_station',
    'restoration_entry':'CompleteVillageBlacksmithRepair','reserved_quest_id':'hills.village.restore_blacksmith',
    'circulation_m':1.4,'station_front_clearance_m':1.6,
    'interior':'rear working bay, side stock shelving, front reception and rest bench'}
plan['blacksmith']={**blacksmith_defaults,**plan.get('blacksmith',{})}
if plan['blacksmith'].get('revision',1)<3:
    plan['layout_revision']='20261117: nine houses, first-house blacksmith, two inward-facing ruined homes; preserve terrain seed/anchor.'
(source/'layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for relative in ['Content/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask.uasset',
                 'Content/WorldGeneration/TemperateHills/AbandonedVillage/M_VillageMudRoad.uasset',
                 'SourceAssets/TemperateHillsVillage/RoadMask.png']:
    target=out/'Before'/relative
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,target)
sys.path.insert(0,str(root/'Tools/WorldGeneration/AbandonedVillage'))
sys.argv=['draw_plan.py','--data-only']
runpy.run_path(str(root/'Tools/WorldGeneration/AbandonedVillage/draw_plan.py'),run_name='__main__')
(out/'design.json').write_text(json.dumps(dict(houses=plan['houses'],roads=new_roads,blacksmith=plan['blacksmith'],
    wall_extent_m=[130,100],terrain_unchanged=True),ensure_ascii=False,indent=2),encoding='utf-8')
