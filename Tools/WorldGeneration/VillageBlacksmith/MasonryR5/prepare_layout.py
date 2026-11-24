"""Remove the smith forecourt wall and reserve the enlarged chimney footprint."""
import json,math,runpy,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
SRC=ROOT/'SourceAssets/TemperateHillsVillage';OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/MasonryR5'
backup=OUT/'Before';backup.mkdir(exist_ok=True)
for name in ('layout.json','RoadMask.png','PlantExclusion.raw','DressingClearance.raw'):
 if not (backup/name).exists():shutil.copy2(SRC/name,backup/name)
plan=json.loads((SRC/'layout.json').read_text(encoding='utf-8'))
plan['blacksmith'].update(chimney_cm=[200,500,0],chimney_shaft_width_cm=146,chimney_style='bonded original house fieldstone and mortar',
    front_wall_clearance_local_m=[-5.4,5.4,-6.2,-4.4],repair_chain_lamps=['workshop','loft','entry','furnace_yard'])
sys.path.insert(0,str(ROOT/'Tools/WorldGeneration/AbandonedVillage'))
from wall_support import remove_blacksmith_front_walls
removed=remove_blacksmith_front_walls(plan)
receipt=OUT/'removed-front-walls.json'
if removed:receipt.write_text(json.dumps(removed,ensure_ascii=False,indent=2),encoding='utf-8')
house=next(h for h in plan['houses'] if h[0]=='01');a=math.radians(house[5])
reserved=[r for r in plan.get('service_clearings',[]) if r.get('owner')!='BlacksmithLoftR3']
for x,y,hx,hy in ((200,500,110,108),(0,-427,390,65)):
 reserved.append(dict(owner='BlacksmithLoftR3',center=[house[3]+(x*math.cos(a)-y*math.sin(a))/100,house[4]+(x*math.sin(a)+y*math.cos(a))/100],half=[hx/100,hy/100],yaw=house[5]))
plan['service_clearings']=reserved
plan['layout_revision']='20261117 MasonryR5: broad bonded stone chimney, open blacksmith forecourt, restoration-only chain lanterns.'
(SRC/'layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sys.argv=['draw_plan.py','--data-only']
try:runpy.run_path(str(ROOT/'Tools/WorldGeneration/AbandonedVillage/draw_plan.py'),run_name='__main__')
except SystemExit as done:
 if done.code not in (None,0):raise
print('SMITH_R5_LAYOUT_SAVED',len(removed),'front wall pieces removed')
