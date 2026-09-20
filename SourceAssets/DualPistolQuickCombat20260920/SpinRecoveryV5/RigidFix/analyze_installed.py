import json,math
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).parent;data=json.loads((P/'installed_dw715.json').read_text());report={}
def rel(world,n):
    r=world['WPN_root'];b=world[n];q=Quaternion(r['q']).inverted()
    return q@(Vector(b['p'])-Vector(r['p'])),q@Quaternion(b['q'])
def angle(a,b):
    q=a.rotation_difference(b);return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
for key,clip in data['clips'].items():
    modes={}
    for mode,rows in clip['samples'].items():
        base=rows[0]['world'];references={n:rel(base,n) for n in base};metrics={'max_relative_position_cm':0.,'max_relative_rotation_deg':0.,'max_root_scale_delta':0.,'max_part_scale_delta':0.,'worst_position':{},'worst_rotation':{},'worst_scale':{}}
        for row in rows:
            world=row['world']
            for n,b in world.items():
                p,q=rel(world,n);oldp,oldq=references[n]
                d=(p-oldp).length;a=angle(q,oldq)
                scale=max(abs(x-y) for x,y in zip(b['s'],base[n]['s']))
                if d>metrics['max_relative_position_cm']:metrics['max_relative_position_cm']=d;metrics['worst_position']={'bone':n,'time':row['time']}
                if a>metrics['max_relative_rotation_deg']:metrics['max_relative_rotation_deg']=a;metrics['worst_rotation']={'bone':n,'time':row['time']}
                if scale>metrics['max_part_scale_delta']:metrics['max_part_scale_delta']=scale;metrics['worst_scale']={'bone':n,'time':row['time'],'scale':b['s'],'base':base[n]['s']}
                if n=='WPN_root':metrics['max_root_scale_delta']=max(metrics['max_root_scale_delta'],scale)
        modes[mode]=metrics
    report[key]=modes
(P/'installed_diagnosis.json').write_text(json.dumps(report,indent=2))
for k,v in report.items():
    if '/r/' in k and k.endswith('quickcombat'):print(k,json.dumps(v),flush=True)
print('DW715_GUN_PARENTS '+json.dumps(next(iter(data['clips'].values()))['parents']),flush=True)
