"""Quantify the requested range diagnosis from the actual compressed UE pose."""
from pathlib import Path
import json, math
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/BiteV33')
source=json.loads((OUT/'before-pose.json').read_text(encoding='utf8'))
radius=42. # FPSGAMECharacter constructor's actual capsule radius, cm.
rows=[]
for frame in source['samples']:
    if frame['time'] not in (.54,.56,.60,.65):continue
    x,y,_=frame['maw']
    for angle in (0.,-35.,35.):
        a=math.radians(angle);projection=x*math.cos(a)+y*math.sin(a)
        perpendicular2=x*x+y*y-projection*projection
        def limit(reach):return projection+math.sqrt(max(0.,(reach+radius)**2-perpendicular2))
        old=limit(source['tuning']['bite_reach']);new=limit(235.)
        rows.append(dict(time=frame['time'],yaw_degrees=angle,old_limit_cm=old,new_limit_cm=new,
            trigger_cm=350.,new_margin_over_trigger_cm=new-350.))
report=dict(scope='Actual compressed bite + analytical capsule/range geometry; no collision world, AI, player input or rendering',
    source_clip=source['clip'],player_capsule_radius_cm=radius,rows=rows,
    old_contact='one attempt at 0.56s, consumed even on a miss',
    new_contact='0.54..0.65s, miss may retry in window; valid/blocked contact consumes once',
    facing_commit_seconds=dict(before=.42,after=.48),gameplay_tested=False)
(OUT/'range-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps([r for r in rows if r['time']==.56],indent=2))
