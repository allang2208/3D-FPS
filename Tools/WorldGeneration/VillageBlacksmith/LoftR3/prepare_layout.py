"""Publish only the smith's enlarged kit and its ground reservations; retain the seed and village."""
import copy,json,math,runpy,shutil,sys
from pathlib import Path
from design import XY_FACTOR,DESCRIPTION
ROOT=Path(__file__).resolve().parents[4]
SRC=ROOT/'SourceAssets/TemperateHillsVillage'
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
for relative in ['SourceAssets/TemperateHillsVillage/'+n for n in ('layout.json','house-pieces.json','RoadMask.png','PlantExclusion.raw','DressingClearance.raw')]+['Source/FPSGAME/WorldGeneration/TemperateVillageLayout.inl']:
    original=ROOT/relative;backup=OUT/'Before'/relative
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
plan=json.loads((SRC/'layout.json').read_text(encoding='utf-8'))
kit=json.loads((SRC/'house-pieces.json').read_text(encoding='utf-8'))
parts=copy.deepcopy(kit['SL_Packed_House_TypeA_00A'])
for part in parts:
    for field in ('pos','center','extent','scale'):
        part[field][0]*=XY_FACTOR;part[field][1]*=XY_FACTOR
kit['SL_Blacksmith_LoftR3']=parts
house=next(h for h in plan['houses'] if h[0]=='01');house[2]='SL_Blacksmith_LoftR3'
plan['blacksmith'].update(DESCRIPTION)
plan['blacksmith']['interior']='Half-open ground forge; upper bedroom with native windows; west return stair; rear external chimney.'
plan['layout_revision']='20261117 LoftR3: blacksmith footprint area +25%; two floors; preserve all other houses, seed and village anchor.'
reserved=[r for r in plan.get('service_clearings',[]) if r.get('owner')!='BlacksmithLoftR3']
a=math.radians(house[5])
for x,y,hx,hy in [(200,500,110,108),(0,-427,390,65)]:
    reserved.append(dict(owner='BlacksmithLoftR3',center=[house[3]+(x*math.cos(a)-y*math.sin(a))/100,house[4]+(x*math.sin(a)+y*math.cos(a))/100],half=[hx/100,hy/100],yaw=house[5]))
plan['service_clearings']=reserved
(SRC/'house-pieces.json').write_text(json.dumps(kit,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(SRC/'layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools/WorldGeneration/AbandonedVillage'))
sys.argv=['draw_plan.py','--data-only']
try:
    runpy.run_path(str(ROOT/'Tools/WorldGeneration/AbandonedVillage/draw_plan.py'),run_name='__main__')
except SystemExit as done:
    if done.code not in (None,0):raise
(OUT/'layout-prepared.json').write_text(json.dumps(dict(house=house,design=DESCRIPTION,service_clearings=reserved,terrain_seed_changed=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('LOFT_R3_LAYOUT_PREPARED')
