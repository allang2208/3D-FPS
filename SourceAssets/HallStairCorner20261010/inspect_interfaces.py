"""Requested dimensional inspection of railing feet and corner source coverage."""
from pathlib import Path
import json,math,runpy
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'geometry.json').read_text('utf8'));issues=[];counts={};margins={}
for p in data['posts']:
    room=p['room'];x,y,z=p['x'],p['y'],p['foot'];half=p['base_half'];counts[room]=counts.get(room,0)+1
    if room=='Reception':
        flights=[(-8,0,1,.34,4.5/28),(-1.64,2.25,1,.34,4.5/28)];width=3.;yc=math.copysign(8.8,y)
        in_gallery=abs(y)-half>=10.5-1e-5 or x+half<=-18+1e-5 or x-half>=16-1e-5
        in_landing=((-3.24<=x-half and x+half<=-1.64 and abs(y-yc)+half<=1.60) or
            (3.12<=x-half and x+half<=5.52 and 7<=abs(y)-half and abs(y)+half<=10.5))
    else:
        flights=[(-5,0,-1,4.7/14,.15),(-11.3,2.1,-1,4.7/14,.15)];width=3.16;yc=math.copysign(15.9,y)
        in_gallery=x+half<=-16+1e-5 and abs(y)+half<=18
        in_landing=-11.3<=x-half and x+half<=-9.7 and abs(y-yc)+half<=width/2
    support=in_gallery or in_landing
    if not support:
        for start,base,d,going,rise in flights:
            for i in range(14):
                a=start+d*i*going;b=a+d*going;lo,hi=sorted((a,b))
                if lo-1e-5<=x-half and x+half<=hi+1e-5 and abs(y-yc)+half<=width/2+1e-5 and abs(z-(base+(i+1)*rise))<1e-5:
                    support=True;margin=width/2-abs(y-yc)-half
                    margins[room]=min(margins.get(room,99),margin)
    if not support:issues.append(p)
lamps=runpy.run_path(str(ROOT/'recipe.py'))['lamps']();corners=[]
for l in lamps:
    x=-2360 if l['position'][0]<0 else 2360;y=math.copysign(1720,l['position'][1]);z=l['corner_floor_z_cm']
    dist=math.dist(l['position'],[x,y,z]);corners.append(dict(id=l['id'],sample=[x,y,z],source_distance_cm=round(dist,2),radius_cm=l['radius'],direction=l['fixture_normal'],steady=True,inside_attenuation=dist<l['radius']))
report=dict(post_count=counts,unsupported_plates=issues,minimum_stair_side_margin_cm={k:round(v*100,2) for k,v in margins.items()},
    corner_sources=corners,existing_hanging_lamps_modified=False,rendered=False,runtime_tested=False,
    note='Dimensional source inspection requested by user. Radius reach does not measure rendered illuminance or occlusion.')
(ROOT/'Receipts/interface-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
if issues:raise RuntimeError('Unsupported railing plates need correction')
