"""Adapt donor palm heading to A762's rolled receiver and native shoulder."""
import json,math,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
d=json.loads((O/'reference_poses.json').read_text());a=d['A762']['samples']['310']['bones'];rest=d['A762']['rest']
p={n:np.array(m) for n,m in a.items()};R={n:np.array(m) for n,m in rest.items()}
donor=d['ASH12']['samples']['140.4'];H=np.array(donor['bones']['hand_r']);pivot=np.array([-.0358,-.1694,.075])
H[:3,3]+=pivot-np.array(donor['bones']['index_03_r'])[:3,3]
A=p['upperarm_r'][:3,3];E0=p['lowerarm_r'][:3,3];l1=np.linalg.norm(E0-A);l2=np.linalg.norm(p['hand_r'][:3,3]-E0)
rest_axis=R['hand_r'][:3,3]-R['lowerarm_r'][:3,3];rest_axis/=np.linalg.norm(rest_axis)
def compute(v):
    Q=Rotation.from_euler('xyz',v,degrees=True).as_matrix();h=H.copy();h[:3,:3]=Q@h[:3,:3];h[:3,3]=pivot+Q@(h[:3,3]-pivot)
    T=h[:3,3];dist=np.linalg.norm(T-A);axis=(T-A)/dist;along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    heading=h[:3,:3]@R['hand_r'][:3,:3].T@rest_axis
    pole=T-heading*l2-A;pole-=axis*np.dot(pole,axis);pole/=np.linalg.norm(pole)
    E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));actual=(T-E)/np.linalg.norm(T-E)
    return np.degrees(np.arccos(np.clip(np.dot(actual,heading),-1,1))),T
print([(y,compute([0,y,0])) for y in [0,45,60,75,90,105,120,135,150,180]],flush=True)
