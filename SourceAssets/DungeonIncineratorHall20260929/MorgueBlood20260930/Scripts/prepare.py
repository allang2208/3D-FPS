"""Reuse the hospital scan and scatter class with B1-specific bounded receivers."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
ward=json.loads((PROJECT/'SourceAssets/DungeonIsolationWard20260929/Config/room.json').read_text(encoding='utf-8'))['blood_scatter']
layout=json.loads((HALL/'MorgueOpenPlan20260930/Config/layout.json').read_text(encoding='utf-8'))
z=layout['floor_z']
def floor(x0,y0,x1,y1):
    return dict(center_m=[(x0+x1)/2,(y0+y1)/2,z+.04],normal=[0,0,1],axis_u=[1,0,0],
                half_size_m=[(x1-x0)/2,(y1-y0)/2],wall=False)
def wall(a,b,normal):
    return dict(center_m=[(a[0]+b[0])/2,(a[1]+b[1])/2,z+1.5],normal=[*normal,0],axis_u=[0,0,1],
                half_size_m=[1.15,math.dist(a,b)/2],wall=True)
def diagonal(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);v=(dx/length,dy/length);n=(-v[1],v[0])
    p=[a[i]+v[i]*.4+n[i]*.14 for i in range(2)]
    q=[b[i]-v[i]*.4+n[i]*.14 for i in range(2)]
    return wall(p,q,n)
hall=[floor(-8.4,-7.2,9.0,4.75),floor(-8.3,-10.0,8.3,-7.2),
      floor(-13.4,-2.15,-8.4,4.75),floor(-13.4,5.55,-5.2,10.0),floor(9.25,.4,13.3,6.8)]
hall += [wall((-8.5,-10.36),(8.5,-10.36),(0,1)),
         wall((-13.86,-2.1),(-13.86,2.5),(1,0)),wall((-13.86,5.5),(-13.86,9.95),(1,0)),
         wall((-13.4,10.36),(-5.15,10.36),(0,-1)),wall((13.86,.4),(13.86,6.9),(-1,0)),
         diagonal((9,-10.5),(14,-7.5)),diagonal((14,7.5),(9,10.5))]
for a,b in [(-4.55,-2.95),(-.05,3.95),(6.85,8.55)]:hall.append(wall((a,5.1),(b,5.1),(0,-1)))
# Each retained room has its own budget. Main-hall picks cannot consume it.
wash=[floor(-4.4,5.65,1.6,9.95),wall((-4.7,5.65),(-4.7,9.95),(1,0)),
      wall((1.9,5.65),(1.9,9.95),(-1,0)),wall((-4.4,10.36),(1.6,10.36),(0,-1)),
      wall((-4.55,5.3),(-2.95,5.3),(0,1)),wall((-.05,5.3),(1.65,5.3),(0,1))]
service=[floor(2.4,5.65,8.4,9.95),wall((2.1,5.65),(2.1,9.95),(1,0)),
         wall((8.7,5.65),(8.7,9.95),(-1,0)),wall((2.4,10.36),(8.4,10.36),(0,-1)),
         wall((2.35,5.3),(3.95,5.3),(0,1)),wall((6.85,5.3),(8.55,5.3),(0,1))]
c=dict(revision='morgue_hospital_blood_v1_20260930',map=layout['map'],actor_class=ward['actor_class'],
       material=ward['material'],source_config='SourceAssets/DungeonIsolationWard20260929/Config/room.json',
       receiver_tag='Incinerator.MorgueBlood.Receiver',receiver_labels=['Incinerator_B1Floor','Incinerator_B1Walls','Incinerator_B1Wainscot'],
       randomize_on_begin_play=True,scanned_size_range_cm=[60.,100.],floor_size_scale=ward['floor_size_scale'],
       groups=[dict(id='Hall',floor_count=34,wall_count=14,surfaces=hall),
               dict(id='Wash',floor_count=8,wall_count=4,surfaces=wash),
               dict(id='Service',floor_count=8,wall_count=4,surfaces=service)],
       total_floor_target=50,total_wall_target=22,tests_run=False)
(ROOT/'Config/blood.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('MORGUE_BLOOD_RECEIVER_CONFIG_AUTHORED')
