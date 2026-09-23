"""Independent corrected architecture; keep accepted start and source rooms intact."""
import json,copy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
old=read(BASE/'DungeonRoomShells20260922/Config/rooms.json')
route=read(BASE/'DungeonRoutes20260922/Config/rooms.json')
extra=read(BASE/'DungeonVentFreight20260922/Config/rooms.json')
treasure=read(BASE/'DungeonTreasure20260922/Config/rooms.json')
parents={r['id']:copy.deepcopy(r) for r in old['rooms'][:2]+route['rooms']+extra['rooms']}
for rid in ('Distribution','Drainage'):
    for door in parents[rid]['openings']:door.update(width=3,height=2.8)
rooms=[];socket_data={};replacements={}
def variant(parent,name,opening=None):
    r=copy.deepcopy(parents[parent]);r.update(id=name,surface_seed_id=parent,source_id=parent,origin_m=[0,0,0],export_kinds=['Shell','Tiles','Frames'])
    if opening:r['openings'].append(opening)
    rooms.append(r);return r
for rid in ('Distribution','Drainage'):replacements[rid]=variant(rid,rid+'_CombatDoor')['id']
original_sockets=read(BASE/'DungeonTreasure20260922/Config/sockets.json')
specs={rid:[(s['id'],next(o for r in treasure['rooms'] if r['id']==s['variant'] for o in r['openings'] if o['id']=='treasure_side')) for s in original_sockets[rid]] for rid in original_sockets}
specs['VentilationLoop']=[('North',dict(edge=4,center=7.5,width=3,height=2.8,id='treasure_side')),('West',dict(edge=6,center=8.5,width=3,height=2.8,id='treasure_side'))]
specs['FreightTransfer']=[('West',dict(edge=7,center=5,width=3,height=2.8,id='treasure_side')),('East',dict(edge=1,center=3,width=3,height=2.8,id='treasure_side'))]
for parent,items in specs.items():
    socket_data[parent]=[]
    for label,opening in items:
        r=variant(parent,parent+'_CombatTreasure'+label,copy.deepcopy(opening));e=opening['edge'];a=r['footprint'][e];b=r['footprint'][(e+1)%len(r['footprint'])]
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);t=opening['center']
        socket_data[parent].append(dict(id=label,variant=r['id'],position=[(a[0]+dx*t/length)*100,-(a[1]+dy*t/length)*100,0],normal=[dy/length,dx/length,0],width=300,height=280))
# Square bend: UE entry at (0,200), exit at (200,0); room bodies remain rigid.
rooms.append(dict(id='RouteElbow',origin_m=[0,0,0],height_m=2.8,footprint=[[-2,-2],[2,-2],[2,2],[-2,2]],
    floors=[[-2,-2,2,2,0]],ceilings=[[-2,-2,2,2,2.8]],openings=[dict(edge=0,center=2,width=3,height=2.8,id='entry'),dict(edge=1,center=2,width=3,height=2.8,id='exit')],columns=[],beams=[],pipes=[],lights=[],anchors=[]))
cfg=dict(version=1,seed=92231,style=old['style'],rooms=rooms,links=[dict(id=rid,origin_m=[0,0,0],axis='y',width=3.24,length=length,height=2.8,light=rid=='Transit') for rid,length in [('Transit',4),('Threshold',.8)]])
(ROOT/'Config/rooms.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/replacements.json').write_text(json.dumps(dict(walls=replacements,sockets=socket_data),indent=2),encoding='utf-8')
print('REPAIR_RECIPES_CREATED',len(rooms))
