"""Author a 10 m clear treasury and optional side-door variants of the accepted rooms."""
import json,copy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROUTES=ROOT.parent/'DungeonRoutes20260922';BASE=ROOT.parent/'DungeonRoomShells20260922'
for d in ('Config','Authored','Receipts'): (ROOT/d).mkdir(exist_ok=True)
old=json.loads((BASE/'Config/rooms.json').read_text(encoding='utf-8'));routes=json.loads((ROUTES/'Config/rooms.json').read_text(encoding='utf-8'))
sources={r['id']:r for r in old['rooms'][:2]+routes['rooms']}
# Wall centres lie 12 cm outside the requested 10 x 10 m clear room.
treasure=dict(id='Treasure',name='宝箱储藏室',origin_m=[0,0,0],height_m=3.45,
 footprint=[[-5.12,0],[5.12,0],[5.12,10.24],[-5.12,10.24]],
 floors=[[-5.12,0,5.12,10.24,0]],ceilings=[[-5.12,0,5.12,10.24,3.45]],
 openings=[dict(edge=0,center=5.12,width=3,height=2.8,id='entry')],
 columns=[[-4.92,3.1],[4.92,3.1],[-4.92,7.1],[4.92,7.1]],
 beams=[[[-5.12,3.1,3.24],[5.12,3.1,3.24]],[[-5.12,7.1,3.24],[5.12,7.1,3.24]]],
 pipes=[dict(points=[[-4.82,.45,3.08],[-4.82,9.8,3.08],[4.82,9.8,3.08]],radius=.065)],
 lights=[dict(at=[0,5.12,3.17],warm=True,lumens=1100,radius_cm=620),dict(at=[0,1.2,3.17],warm=False,lumens=430,radius_cm=320)],
 anchors=[dict(role='treasure_chest',at=[0,5.12,0]),dict(role='treasure_entry',at=[0,1.5,0])],
 # Floor inset marks the reward position without adding a blocking platform.
 accents=[dict(center=[0,5.12,.004],size=[2.6,2.2,.008],material='BareSteel')])
variants=[];sockets={}
for parent,specs in {
 'Distribution':[(7,sources['Distribution']['footprint'][7][1]-6.7,'West'),(6,sources['Distribution']['footprint'][6][0]-3.0,'North')],
 'Drainage':[(5,sources['Drainage']['footprint'][5][1]-9.2,'West'),(1,4.0,'East')],
 'ShoredBreach':[(5,sources['ShoredBreach']['footprint'][5][1]-3.8,'West'),(0,5.4,'South')]
}.items():
    sockets[parent]=[]
    for edge,center,label in specs:
        room=copy.deepcopy(sources[parent]);room.update(id=parent+'_Treasure'+label,origin_m=[0,0,0],surface_seed_id=parent)
        opening=dict(edge=edge,center=center,width=3,height=2.8,id='treasure_side')
        room['openings'].append(opening);room['export_kinds']=['Shell','Tiles','Frames'];variants.append(room)
        a=room['footprint'][edge];b=room['footprint'][(edge+1)%len(room['footprint'])];dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        sockets[parent].append(dict(id=label,variant=room['id'],position=[(a[0]+dx/length*center)*100,-(a[1]+dy/length*center)*100,0],normal=[dy/length,dx/length,0],width=300,height=280))
config=dict(version=1,seed=92231,style=old['style'],rooms=[treasure]+variants,
 links=[dict(id='TreasureLink',origin_m=[0,0,0],axis='y',width=3.24,length=2,height=2.8,light=False)])
(ROOT/'Config/rooms.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/sockets.json').write_text(json.dumps(sockets,indent=2))
rules=json.loads((ROUTES/'Config/rules.json').read_text());rules.setdefault('treasure_chance_per_room',.1)
rules['treasure_max_per_room']=1
(ROUTES/'Config/rules.json').write_text(json.dumps(rules,indent=2))
print('TREASURE_RECIPES_WRITTEN',len(variants),'side-door variants')
