"""Summarize actual compressed arm motion in both native player skeletons."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/ArmrestExit20261024'
data=json.loads((OUT/'saved_arm_samples.json').read_text())
report={}
for variant,body in data.items():
    report[variant]={}
    names=body['bones']
    for label in ('previous','current'):
        report[variant][label]={}
        for role,take in body[label].items():
            local=np.array([v['local'] for v in take['samples']])
            world=np.array([v['world'] for v in take['samples']])
            lateral=world[:,names.index('upperarm_l'),:3]-world[:,names.index('upperarm_r'),:3]
            lateral/=np.linalg.norm(lateral,axis=1)[:,None]
            row={}
            for side,sign in (('l',1),('r',-1)):
                indexes=[names.index(n+'_'+side) for n in ('upperarm','lowerarm','hand')]
                shoulder,elbow,hand=world[:,:,:3][:,indexes].transpose(1,0,2)
                up,lo=elbow-shoulder,hand-elbow
                normal=np.cross(up,lo);normal/=np.linalg.norm(normal,axis=1)[:,None]
                plane_step=np.degrees(np.arccos(np.clip((normal[1:]*normal[:-1]).sum(axis=1),-1,1)))
                steps={}
                for name,i in zip(('upperarm','lowerarm','hand'),indexes):
                    q=R.from_quat(local[:,i,3:7])
                    steps[name]=float(np.degrees((q[1:]*q[:-1].inv()).magnitude()).max())
                row[side]={'max_joint_frame_degrees':steps,'max_elbow_plane_step_degrees':float(plane_step.max()),
                           'min_elbow_outside_shoulder_cm':float((sign*((elbow-shoulder)*lateral).sum(axis=1)).min())}
            report[variant][label][role]=row
    seams={}
    for role,take in body['current'].items():
        old=body['previous'][role]
        errors=[]
        for i in (0,-1):
            a=np.array(old['samples'][i]['world']);b=np.array(take['samples'][i]['world'])
            errors.append({'position_cm':float(np.linalg.norm(a[:,:3]-b[:,:3],axis=1).max()),
                           'rotation_degrees':float(np.degrees((R.from_quat(a[:,3:7]).inv()*R.from_quat(b[:,3:7])).magnitude()).max())})
        seams[role]=errors
    report[variant]['endpoints_vs_previous']=seams
(OUT/'saved_arm_review.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
