"""Inspect newly hanging palms and fingers against the torso and thighs."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/HangingEntryV6')
sys.argv=['body-contact','--','--candidate','--all','--review',str(OUT/'BodyContact'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
hand_names=('hand_','thumb_','index_','middle_','ring_','pinky_')
hand_ids=np.array([i for i,b in enumerate(dom) if b.startswith(hand_names)])[::3]
def arm_branch(name):
    bone=ix[name]
    while bone>=0:
        if names[bone].startswith(('clavicle_','upperarm_')):return True
        bone=parents[bone]
    return False
# Corrective wrist/elbow bones belong to the arm too; testing a hand against
# its own wrist surface is not a torso/thigh penetration.
body_mask=np.array([not arm_branch(b) for b in dom])
body_tri=tri[np.all(body_mask[tri],axis=1)]
def inside(tree,point):
    votes=0
    for vector in ((1,.37,.21),(-.22,1,.41),(.31,-.18,1)):
        direction=Vector(vector).normalized();origin=Vector(point);hits=0
        for _ in range(64):
            loc,_,_,_=tree.ray_cast(origin,direction,500)
            if loc is None:break
            hits+=1;origin=loc+direction*.003
        votes+=hits%2
    return votes>=2
rows=[]
for kind in ('Sofa','SofaLeft','SofaRight'):
    data=rig['clips'][f'Rest.{kind}.Enter']
    for t in (0,.35,.7,1.05,1.4):
        f=np.array(data['frames'][round(t*30)]);v=skin(f);w=fk(f)
        tree=BVHTree.FromPolygons(v.tolist(),body_tri.tolist(),all_triangles=True)
        probe=Vector(w[ix['pelvis'],:3,3]+[80,0,0]);p,n,_,_=tree.find_nearest(probe)
        sign=1 if n.dot(probe-p)>0 else -1
        worst=[]
        for j in hand_ids:
            p,n,face,dist=tree.find_nearest(Vector(v[j]),5)
            if p is not None and dist>.5 and n.dot(Vector(v[j])-p)*sign<-.5 and inside(tree,v[j]):
                worst.append([float(dist),dom[j],v[j].tolist(),[dom[k] for k in body_tri[face]]])
        row={'kind':kind,'time':t,'penetrating_samples':len(worst),'worst':sorted(worst,reverse=True)[:3]}
        rows.append(row);print('HANGING_BODY_CONTACT',kind,t,len(worst),row['worst'][:1],flush=True)
(OUT/'hand_body_contact.json').write_text(json.dumps(rows,indent=2))
