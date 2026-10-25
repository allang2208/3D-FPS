"""Check hands against torso/thigh surfaces throughout the new bed entry."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--root')+1]) if '--root' in sys.argv else Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
saved='--saved' in sys.argv
selected_phase=sys.argv[sys.argv.index('--phase')+1] if '--phase' in sys.argv else None
sys.argv=['body-contact','--','--v2' if saved else '--candidate','--all','--review',str(OUT/('ReviewSaved' if saved else 'BodyContact')),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
hand_ids=np.array([i for i,b in enumerate(dom) if b.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))])[::3]
def arm_branch(name):
    bone=ix[name]
    while bone>=0:
        if names[bone].startswith(('clavicle_','upperarm_')):return True
        bone=parents[bone]
    return False
body_mask=np.array([not arm_branch(b) for b in dom]);body_tri=tri[np.all(body_mask[tri],axis=1)]
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
for kind in sorted({k.split('.')[1] for k in rig['clips']}):
    worst=[];count=0;pose_count=0
    for phase in ((selected_phase,) if selected_phase else ('Enter','Idle','Exit') if saved else ('Enter','Idle')):
        data=rig['clips'][f'Rest.{kind}.{phase}'];a=np.array(data['frames'])
        step=1 if saved else max(1,round((len(a)-1)/data['duration']/10))
        samples=sorted(set(list(range(0,len(a),step))+[len(a)-1])) if phase!='Idle' else [0,len(a)//2,len(a)-1]
        for j in samples:
            t=j*data['duration']/(len(a)-1);v=skin(a[j]);w=fk(a[j]);pose_count+=1
            tree=BVHTree.FromPolygons(v.tolist(),body_tri.tolist(),all_triangles=True)
            probe=Vector(w[ix['pelvis'],:3,3]+[80,0,0]);p,n,_,_=tree.find_nearest(probe);sign=1 if n.dot(probe-p)>0 else -1
            for i in hand_ids:
                p,n,face,dist=tree.find_nearest(Vector(v[i]),8)
                if p is not None and dist>.5 and n.dot(Vector(v[i])-p)*sign<-.5 and inside(tree,v[i]):
                    count+=1;worst.append([float(dist),phase,round(t,3),dom[i],v[i].tolist(),[dom[k] for k in body_tri[face]]])
    row={'kind':kind,'poses':pose_count,'penetrating_samples':count,'worst':sorted(worst,reverse=True)[:8]};rows.append(row)
    print('BED_BODY_CONTACT',kind,pose_count,count,row['worst'][:1],flush=True)
(OUT/('hand_body_contact_saved.json' if saved else 'hand_body_contact.json')).write_text(json.dumps(rows,indent=2))
