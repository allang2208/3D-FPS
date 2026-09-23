"""New junction, through-variant and connector; accepted room recipes stay unchanged."""
import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent/'DungeonRoomShells20260922'
base=json.loads((SOURCE/'Config/rooms.json').read_text(encoding='utf-8'))
breach=copy.deepcopy(next(r for r in base['rooms'] if r['id']=='ShoredBreach'))
# Exit is in the lower east boundary, separated from the upper ancient side pocket.
breach['origin_m']=[0,0,0]
breach['openings'].append(dict(edge=1,center=6.2,width=3,height=2.8,id='exit'))
junction=dict(id='Junction',name='多门管线枢纽',origin_m=[0,0,0],height_m=3.65,
 footprint=[[-7,0],[7,0],[7,12],[-7,12]],floors=[[-7,0,7,12,0]],ceilings=[[-7,0,7,12,3.65]],
 openings=[dict(edge=e,center=c,width=3,height=2.8,id=k) for e,c,k in [(0,7,'entry'),(1,6,'right'),(2,7,'forward'),(3,6,'left')]],
 columns=[[-3.5,3.4],[3.5,3.4],[-3.5,8.6],[3.5,8.6]],
 beams=[[[-7,y,3.42],[7,y,3.42]] for y in [3.4,8.6]],
 pipes=[dict(points=[[-6.55,.45,3.05],[-6.55,11.55,3.05],[6.55,11.55,3.05],[6.55,.45,3.05]],radius=.095)],
 lights=[dict(at=[x,y,3.34],warm=warm,lumens=520,radius_cm=500) for x,y,warm in [(0,1.5,False),(-5.1,6,True),(5.1,6,False),(0,10.5,False)]],
 anchors=[dict(role='route_choice',at=[0,5.5,0]),dict(role='future_encounter',at=[0,7.5,0])])
cap=dict(id='RouteEnd',name='末端检修开间',origin_m=[0,0,0],height_m=3.15,
 footprint=[[-2.2,0],[2.2,0],[2.2,4],[-2.2,4]],floors=[[-2.2,0,2.2,4,0]],ceilings=[[-2.2,0,2.2,4,3.15]],
 openings=[dict(edge=0,center=2.2,width=3,height=2.8,id='entry')],
 columns=[],beams=[],pipes=[dict(points=[[-1.85,.4,2.85],[-1.85,3.6,2.85],[1.85,3.6,2.85]],radius=.07)],
 lights=[dict(at=[0,2.9,2.94],warm=True,lumens=350,radius_cm=360)],
 anchors=[dict(role='future_route',at=[0,3,0])])
data=dict(version=1,seed=92247,target_map='/Game/GameMaps/L_Dungeon_Randomized',style=base['style'],rooms=[breach,junction,cap],links=[dict(id='Transit',origin_m=[0,0,0],axis='y',width=3,length=4,height=3.15)])
data['links'].append(dict(id='Threshold',origin_m=[0,0,0],axis='y',width=3,length=.8,height=3.15,light=False))
(ROOT/'Config/rooms.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/rules.json').write_text(json.dumps(dict(version=1,treasure_chance_per_room=.1,treasure_max_per_room=1,rooms_per_group=[3,5],junction_exits=['forward','left','right'],short_link_m=.8,group_corridor_m=12,branch_lead_m=24,seed=92247,scale_locked=True,randomness=['room_order','room_entry_direction','group_length'],start_exit_cm=[2400,-1800,94],start_direction=[0,-1,0],reserved_start_cm=[[-100,-1800,-50],[3500,1200,800]]),indent=2))
print('ROUTE_MODULE_RECIPES_WRITTEN')
