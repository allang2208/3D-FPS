"""Reuse ThrustElbowRepair's existing support solver on the SVD native rig."""
from pathlib import Path
import sys,json,gzip,math,numpy as np
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
P=O.parents[2]
sys.path.insert(0,str(P/'SourceAssets/ThrustElbowRepair20260923'))
import elbow_support as solver
inputs=O.parent/'ForegripFit20261019/Inputs'
with gzip.open(inputs/'motion.json.gz','rt') as f: motion=json.load(f)
with gzip.open(inputs/'arms.json.gz','rt') as f: arms=json.load(f)
names=motion['names'];ids={n:i for i,n in enumerate(names)}
def unpack(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
rest={n:unpack(v) for n,v in zip(names,arms['reference'])}
axis=rest['hand_r'].translation-rest['lowerarm_r'].translation
stations={'r':{n:(rest[n].translation-rest['lowerarm_r'].translation).dot(axis)/axis.length_squared for n in ('lowerarm_twist_01_r','lowerarm_twist_02_r')}}
solver.DISTAL_LOCK_STATION=stations['r']['lowerarm_twist_01_r']
input_file=O/'poses-before-elbow-support.npz'
input_file.write_bytes((O/'poses.npz').read_bytes())
data=np.load(input_file);out={k:data[k].copy() for k in data.files}
state={};times=motion['clips']['quick_melee']['times'];duration=motion['clips']['quick_melee']['duration']
patch=[];rows=[];maximum_step=0.;last={}
for i,raw in enumerate(data['base']):
    source={n:Matrix(m.tolist()) for n,m in zip(names,raw)}
    weight=solver.smooth(times[i]/.12)*solver.smooth((duration-times[i])/.12)
    result=solver.support_elbow(source,rest,stations,'r',state,weight)
    delta={}
    for n,m in result.items():
        # Existing solver changes rotations only. Keep input translations and
        # scales at their original precision when transferring the result.
        rotation=m.to_quaternion()@source[n].to_quaternion().inverted()
        delta[n]=np.array(rotation.to_matrix())
        if n in last:
            maximum_step=max(maximum_step,math.degrees(2*math.acos(min(1.,abs(rotation.dot(last[n]))))))
        last[n]=rotation.copy()
    patch.append(delta);rows.append({'frame':i,'weight':weight,'source_seam_degrees':math.degrees(state.get('r_seam',0.))})
for family,poses in out.items():
    for i,p in enumerate(poses):
        for n,turn in patch[i].items():p[ids[n],:3,:3]=turn@p[ids[n],:3,:3]
np.savez_compressed(O/'poses.npz',**out)
(O/'elbow-support-receipt.json').write_text(json.dumps({'solver':str(P/'SourceAssets/ThrustElbowRepair20260923/elbow_support.py'),
    'stations':stations,'wrist_lock_station':solver.DISTAL_LOCK_STATION,'joint_positions_unchanged':True,
    'hand_fingers_gun_unchanged':True,'maximum_correction_step_degrees':maximum_step,'rows':rows},indent=2))
print('EXISTING_SVD_ELBOW_SUPPORT_APPLIED',maximum_step,flush=True)
