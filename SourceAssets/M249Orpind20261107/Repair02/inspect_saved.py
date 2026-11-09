"""Compare saved compressed arm poses and ADS geometry for the requested repair."""
from pathlib import Path
import json,pickle
import numpy as np
from scipy.spatial.transform import Rotation

root=Path(__file__).resolve().parent
def load(n):
    with (root/n).open('rb') as f:return pickle.load(f)
def matrix(t):
    t=np.asarray(t);m=np.zeros(t.shape[:-1]+(4,4));m[...,3,3]=1
    m[...,:3,:3]=Rotation.from_quat(t[...,3:7].reshape(-1,4)).as_matrix().reshape(t.shape[:-1]+(3,3))*t[...,None,7:10]
    m[...,:3,3]=t[...,:3];return m
def normalized(state,role):
    rig=load(state+'_rig.pkl');clip=load(state+'_'+role+'.pkl')
    frames=matrix(clip['frames']);idx=rig['names'].index('WPN_root')
    transform=matrix(rig['bind'][idx])@np.linalg.inv(frames[:,idx])
    return dict(zip(rig['names'],np.swapaxes(transform[:,None]@frames,0,1))),clip
def rotation(m):return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2,keepdims=True)
def angle(a,b):return np.degrees(Rotation.from_matrix(rotation(a)@np.swapaxes(rotation(b),-1,-2)).magnitude())
report={}
for role in ('reload','reload_empty'):
    role_report={}
    for state in ('before','after'):
        poses,clip=normalized(state,role)
        arms=[n for n in poses if any(n.startswith(s) for s in ('upperarm','lowerarm','hand_'))]
        jumps={n:angle(poses[n][1:],poses[n][:-1]) for n in arms}
        worst=max(jumps,key=lambda n:jumps[n].max())
        data=dict(max_frame_angle_deg=float(jumps[worst].max()),worst_bone=worst,
                  worst_time=float((jumps[worst].argmax()+1)*clip['duration']/(len(jumps[worst]))))
        if state=='after':
            idle,_=normalized('after','idle')
            data['end_idle_angle_deg']={n:float(angle(poses[n][-1],idle[n][0])) for n in arms}
            data['end_idle_distance_cm']={n:float(np.linalg.norm(poses[n][-1,:3,3]-idle[n][0,:3,3])) for n in arms}
            authored=np.load(root/(role+'_world.npz'))
            data['authored_saved_max_angle_deg']=max(float(angle(poses[n],authored[n]).max()) for n in arms)
            data['authored_saved_max_distance_cm']=max(float(np.linalg.norm(poses[n][:,:3,3]-authored[n][:,:3,3],axis=1).max()) for n in arms)
        role_report[state]=data
    report[role]=role_report
poses,_=normalized('after','idle')
rear=poses['WPN_RearSight'][0,:3,3];front=poses['WPN_FrontSight'][0,:3,3]
axis=(front-rear)/np.linalg.norm(front-rear)
up=rotation(poses['WPN_root'][0])@np.array([-.0871557,0,.9961947]);up=up-axis*np.dot(axis,up);up/=np.linalg.norm(up)
ads=np.stack((axis,np.cross(up,axis),up))
report['ads']=dict(front_cm=front.tolist(),rear_cm=rear.tolist(),up=up.tolist(),
                   aligned_axis=(ads@axis).tolist(),aligned_art_up=(ads@np.array([0,0,1.])).tolist())
(root/'saved_inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
