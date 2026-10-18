"""Review the saved family through entry, hold, bite and release on V8 skin."""
import sys,json,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));import pose_model as P
before=json.loads((O/'before_motion.json').read_text());after=P.data['roasted_large_lamb']
food=BVHTree.FromPolygons(P.geometry['vertices'],P.geometry['faces'])
def inside(p):
    votes=0
    for direction in [(1,.371,.619),(-.417,1,.293),(.269,-.529,1)]:
        d=Vector(direction).normalized();o=Vector(p);hits=0
        for _ in range(24):
            hit,_,_,_=food.ray_cast(o,d,100)
            if hit is None:break
            hits+=1;o=hit+d*.0001
        votes+=hits%2
    return votes>=2
ids={s:np.where(sum(P.weights[f'thumb_{j:02}_{s}'] for j in range(1,4))>.025)[0] for s in ['l','r']}
report={'scope':'Offline source-equivalent V8 skin/gesture diagnosis, not game acceptance','phases':{},'unchanged':{}}
for field in ['keys','times','palm_rotation','right_palm_rotation','grip_in_palm','right_grip_in_palm','grip_in_object','right_grip_in_object','object_rotation','bite_in_object']:
    report['unchanged'][field]=before[field]==after[field]
report['unchanged']['four_fingers']=all(before[f][d]==after[f][d] for f in ['digits','right_digits'] for d in ['index','middle','ring','pinky'])
for label,motion in [('before',before),('after',after)]:
    phases={};length_error=0;sidebend=0
    for t in [.1,.3,.55,1,1.65,2.75,3.75,4.65,4.9,5.3,5.6,5.65,5.8]:
        verts,obj,goal,info=P.solve(motion,t);points=(np.column_stack((verts,np.ones(len(verts))))@np.array(obj.inverted()).T)[:,:3]
        row={}
        for side in ['l','r']:
            distances=[]
            for p in points[ids[side]]:
                _,_,_,dist=food.find_nearest(Vector(p));distances.append(-dist if dist<1.2 and inside(p) else dist)
            angles=[]
            for j in range(1,4):
                n=f'thumb_{j:02}_{side}';p=P.parent[n];length_error=max(length_error,abs((goal[n].translation-goal[p].translation).length-P.local[n].translation.length))
                delta=(goal[p]@P.local[n]).to_quaternion().inverted()@goal[n].to_quaternion()
                if delta.w<0:delta.negate()
                # Rotation-vector off the native flexion Y, not an anatomical clinical measurement.
                angle=math.degrees(delta.angle);off=angle*math.sqrt(delta.axis.x**2+delta.axis.z**2)
                if j>1:sidebend=max(sidebend,off)
                angles.append(dict(joint=j,angle_deg=angle,off_hinge_deg=off))
            row[side]=dict(max_thumb_depth_cm=max(0,-min(distances)),vertices_inside_0_5mm=sum(d<-.05 for d in distances),joints=angles)
        phases[str(t)]=row
    report['phases'][label]=phases;report[label+'_max_thumb_bone_length_error_cm']=length_error;report[label+'_max_mcp_ip_off_hinge_deg']=sidebend
source=json.loads((O/'Before/Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8'))
report['unchanged']['other_consumables']=all(v==P.data[k] for k,v in source.items() if k!='roasted_large_lamb')
(O/'saved_pose_review.json').write_text(json.dumps(report,indent=2))
P.render(after,2.75,'final_present');P.render(after,4.65,'final_bite')
print(json.dumps({k:v for k,v in report.items() if k!='phases'},indent=2))
