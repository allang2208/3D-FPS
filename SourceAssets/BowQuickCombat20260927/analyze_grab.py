import bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).parent
old=P.parent/'BowQuickCombat20260926/author_action.py'
ns={'__file__':str(old)}
exec(compile(old.read_text().split('bpy.ops.wm.open_mainfile')[0],str(old),'exec'),ns)
data=ns['ns']['data'];R=ns['R'];rest=ns['rest']
actual=json.loads((P/'imported-before.json').read_text())
indices=[i for i,w in enumerate(data['weights']) if sum(v for n,v in w.items() if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>0.8]
off=Vector((0,32,-12));rows=[]
for row in actual['poses']:
    t=row['t'];w=ns['pose'](t);skin={n:m@rest[n].inverted() for n,m in w.items()}
    pts=[sum((skin[n]@(R@Vector(data['positions'][i]))*v for n,v in data['weights'][i].items()),Vector())+off for i in indices]
    framed={}
    for vfov in (60,75,90):
        tan=math.tan(math.radians(vfov/2))
        def proj(v):return (.5+v.y/(2*v.x*tan*16/9),.5-v.z/(2*v.x*tan)) if v.x>1 else (-10,-10)
        screen=[proj(v) for v in pts]
        framed[str(vfov)]={'inside_fraction':sum(0<x<1 and 0<y<1 for x,y in screen)/len(screen),'center':proj(sum(pts,Vector())/len(pts))}
    delta=max((w[n].translation-Vector(row['bones'][n]['p'])).length for n in ('hand_l','hand_r','bow_grip'))
    rows.append({'t':t,'source_to_import_position_error_cm':delta,'framing':framed})
(P/'framing-before.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
