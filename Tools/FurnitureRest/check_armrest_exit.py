"""Compare exit elbow planes, joint steps, endpoints and unchanged body tracks."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ArmrestExit20261024'
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,ix=ns['fk'],ns['ix']
old=json.loads((OUT.parent/'ChairReuse20261024/authored.json').read_text())
new=json.loads((OUT/'authored.json').read_text())
result={}
for label,rig in [('previous',old),('current',new)]:
    report={}
    for kind in ('Chair50','Chair52'):
        a=np.array(rig['clips'][f'Rest.{kind}.Exit']['frames'])
        world=np.array([fk(f) for f in a]);row={}
        for side in ('l','r'):
            ids=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
            shoulder,elbow,hand=world[:,:,:3,3][:,ids].transpose(1,0,2)
            upper,lower=elbow-shoulder,hand-elbow
            plane=np.cross(upper,lower);plane/=np.linalg.norm(plane,axis=1)[:,None]
            dp=np.degrees(np.arccos(np.clip((plane[1:]*plane[:-1]).sum(axis=1),-1,1)))
            bend=np.degrees(np.arccos(np.clip((upper*lower).sum(axis=1)/(np.linalg.norm(upper,axis=1)*np.linalg.norm(lower,axis=1)),-1,1)))
            bone_steps={}
            for bone in ('upperarm','lowerarm','hand'):
                q=R.from_quat(a[:,ix[bone+'_'+side],3:7]);step=np.degrees((q[1:]*q[:-1].inv()).magnitude())
                bone_steps[bone]={'max_degrees':float(step.max()),'time':(int(np.argmax(step))+1)/30}
            row[side]={'local_bone_steps':bone_steps,'max_elbow_plane_step_deg':float(dp.max()),
                       'bend_degrees':[float(bend.min()),float(bend.max())],
                       'min_outward_elbow_cm':float(((elbow-shoulder)[:,0]*(1 if side=='l' else -1)).min())}
        report[kind]=row
    result[label]=report
    print(label,json.dumps(report),flush=True)
unchanged={}
for kind in ('Chair50','Chair52'):
    role=f'Rest.{kind}.Exit';a=np.array(old['clips'][role]['frames']);b=np.array(new['clips'][role]['frames'])
    body=[]
    for i,name in enumerate(new['names']):
        ancestor=i
        while ancestor>=0 and not new['names'][ancestor].startswith('clavicle_'):
            ancestor=new['parents'][ancestor]
        if ancestor<0:body.append(i)
    unchanged[kind]={'non_arm_tracks_identical':bool(np.array_equal(a[:,body],b[:,body])),
                     'first_pose_identical':bool(np.array_equal(a[0],b[0])),
                     'last_pose_identical':bool(np.array_equal(a[-1],b[-1])),
                     'local_positions_scales_identical':bool(np.array_equal(a[:,:,:3],b[:,:,:3]) and np.array_equal(a[:,:,7:],b[:,:,7:]))}
result['preservation']=unchanged
(OUT/'arm_metrics.json').write_text(json.dumps(result,indent=2))
print('PRESERVATION',json.dumps(unchanged),flush=True)
