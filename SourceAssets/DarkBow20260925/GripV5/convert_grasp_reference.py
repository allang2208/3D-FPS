"""Convert the accepted Blender grasp through its actual native bind frame."""
import json
import numpy as np
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[2]
b=json.loads((P/'grasp_reference.json').read_text())
u=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources/M4.json').read_text())['bones']
names=[n for n in u if n in b['rest'] and any(v in n for v in ('upperarm','lowerarm','hand_','index_','middle_','ring_','pinky_','thumb_'))]
x=np.array([np.array(b['rest'][n])[:3,3] for n in names]);y=np.array([u[n]['position'] for n in names])
W=np.eye(4);W[:3]=np.linalg.lstsq(np.c_[x,np.ones(len(x))],y,rcond=None)[0].T
g=np.array(b['grip']);pos=(W@g)[:3,3]
up=W[:3,:3]@g[:3,2];up/=np.linalg.norm(up)
front=W[:3,:3]@g[:3,0];front-=up*front.dot(up);front/=np.linalg.norm(front)
G=np.eye(4);G[:3,:3]=np.stack([front,np.cross(up,front),up],axis=1);G[:3,3]=pos
out={'source':b['source'],'grip_in_source':G.tolist(),'pose':{}}
for n in names:
    r=np.eye(4);axes=np.array(u[n]['axes']).T
    r[:3,:3]=axes/np.linalg.norm(axes,axis=0);r[:3,3]=u[n]['position']
    pu=W@np.array(b['pose'][n])@np.linalg.inv(np.array(b['rest'][n]))@np.linalg.inv(W)@r
    out['pose'][n]=pu.tolist()
(P/'grasp_native.json').write_text(json.dumps(out),encoding='utf-8')
