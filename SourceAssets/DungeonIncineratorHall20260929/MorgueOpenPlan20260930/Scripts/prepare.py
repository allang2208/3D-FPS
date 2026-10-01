"""Create the new layout and reuse inventory from the saved B1 source; no tests."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;OLD=HALL/'MorgueB120260930'
for p in ('Config','Authored','Receipts'):(ROOT/p).mkdir(parents=True,exist_ok=True)
c=json.loads((OLD/'Config/layout.json').read_text(encoding='utf-8'))
hall=json.loads((HALL/'Config/room.json').read_text(encoding='utf-8'))
c.update(revision='morgue_open_plan_v2_20260930',ue_base='/Game/Dungeons/IncineratorHall20260929/MorgueOpenPlanV2',
         outline_m=hall['hall']['outline'],rect_m=[-14,-10.5,14,10.5],
         door_frame_wall_recess_m=.006,door_frame_depth_m=.28,
         zones=[{'id':'open_mortuary_hall','description':'Continuous receiving and cold storage hall, no foyer partition'},
                {'id':'preparation_and_wash','rect_m':[-4.8,5.2,2,10.36]},
                {'id':'cold_service','rect_m':[2,5.2,8.8,10.36]}])
for module in c['freezer_modules']:module['origin'][0]=11.15
for item,p,yaw in zip(c['props'],[[7.8,-1.9,-3.6],[-8,2.5,-3.6],[-1.5,7.75,-3.6],[.95,9.98,-3.6],[-10.0,1.6,-3.6]],[90,0,90,0,0]):
    item.update(origin=p,yaw=yaw)
c['transfer_door']={'origin':[-13.79,4.0,-3.6],'yaw':90}
c['lights']=c['lights'][:2]+[
 {'id':'Receiving','position':[-9,.5,-.58],'lumens':1000,'radius_cm':650,'shadow':True},
 {'id':'OpenSouth','position':[-2.5,-6.8,-.58],'lumens':1100,'radius_cm':730,'shadow':False},
 {'id':'OpenCentre','position':[2,.4,-.58],'lumens':1100,'radius_cm':750,'shadow':False},
 {'id':'ColdFront','position':[8.3,-2.1,-.58],'lumens':1050,'radius_cm':610,'shadow':True},
 {'id':'NorthWest','position':[-9,7.0,-.58],'lumens':800,'radius_cm':620,'shadow':False},
 {'id':'Wash','position':[-1.4,7.8,-.58],'lumens':650,'radius_cm':500,'shadow':False},
 {'id':'Service','position':[5.4,7.8,-.58],'lumens':500,'radius_cm':500,'shadow':False}]
(ROOT/'Config/layout.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
# Reuse the original readable sign artwork author, changing the former room title.
source=(OLD/'Scripts/author_textures.py').read_text(encoding='utf-8').replace("'遗体转运前室'","'登记与转运区'")
(ROOT/'Scripts/author_textures.py').write_text(source,encoding='utf-8')
print('MORGUE_OPEN_LAYOUT_PREPARED',flush=True)
