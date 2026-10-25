"""Measure feet/seat handover and the skin of the supporting palm pads."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/MeshyBedSupportedHands20261024')
saved='--saved' in sys.argv
sys.argv=['review','--','--v2' if saved else '--candidate','--all','--review',str(BASE/('ReviewSaved' if saved else 'ContactReview')),'--config',str(BASE/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text();exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
groot=BASE.parent/'RefineV2/Geometry';lookup=json.loads((groot/'index.json').read_text());bed=json.loads((groot/lookup[profiles['Bed']['mesh']]).read_text())
bvh=BVHTree.FromPolygons(bed['positions'],bed['triangles'],all_triangles=True)
dominant=[geo['bone_names'][max(ws,key=lambda p:p[1])[0]] for ws in geo['weights']];hip=fk(ref)[ix['pelvis'],:3,3]
seat=np.array([i for i,n in enumerate(dominant) if (n=='pelvis' or n.startswith('thigh')) and np.linalg.norm(points[i]-hip)<25])
feet=np.array([i for i,n in enumerate(dominant) if n.startswith(('foot_','ball_'))])
pads={s:np.array([i for i,n in enumerate(dominant) if n=='hand_'+s]) for s in ('l','r')}
def gap(vertices):
    values=[]
    for p in vertices:
        hit,_,_,_=bvh.ray_cast(Vector(p)+Vector((0,0,30)),Vector((0,0,-1)),120)
        if hit is not None:values.append(float(p[2]-hit.z))
    return min(values) if values else None
rows=[];frames=np.asarray(rig['clips']['Rest.Bed.Enter']['frames'])
for time in (.4,.6,.7,.8,.9,1.,1.5,2.8,3.5,4.3,4.7,5.,5.5,6.,6.5,7.3,8.9):
    v=skin(frames[round(time*30)]);rows.append({'time':time,'feet_floor_gap_cm':float(v[feet,2].min()),'seat_gap_cm':gap(v[seat]),'palm_pad_gap_cm':{s:gap(v[ids]) for s,ids in pads.items()}})
report={'source':'compressed' if saved else 'authored','samples':rows}
(BASE/('support_contacts_saved.json' if saved else 'support_contacts.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(rows,indent=2))
