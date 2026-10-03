"""Diagnose installed left-arm binding, not historical rest-pose proxies."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'current_mesh.json').read_text())
clips=json.loads((HERE/'current_poses.json').read_text())
def mat(b):
    m=np.eye(4); m[:3,:3]=np.array(b['axes']).T; m[:3,3]=b['position']; return m
rest={n:mat(b) for n,b in d['bones'].items()}
V=np.array(d['positions']); W=d['weights']
E=rest['lowerarm_l'][:3,3]; H=rest['hand_l'][:3,3]
f=H-E; length=np.linalg.norm(f); f/=length
t=(V-E)@f/length
left=np.array([sum(v for n,v in w.items() if n.endswith('_l'))>.99 for w in W])
names=['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
report={'bone_stations':{},'clips':{}}
for n in names:
    weight=np.array([w.get(n,0) for w in W])
    report['bone_stations'][n]={'head_station':float((rest[n][:3,3]-E)@f/length),'weight_centroid':float(weight@t/weight.sum())}
for path,a in clips.items():
    frame=a['frames'][0]; skin={n:mat(b)@np.linalg.inv(rest[n]) for n,b in frame.items()}
    fold=[]
    for n in names[:-1]:
        q=skin[n][:3,:3].T@skin['hand_l'][:3,:3]
        fold.append([n,round(float(np.degrees(Rotation.from_matrix(q).magnitude())),2)])
    raw_comp=max(np.abs(mat(frame[n])-mat(a['compressed_start'][n])).max() for n in frame)
    report['clips'][path]={'source':a['source'],'raw_compressed_start_matrix_max_difference':float(raw_comp),'skin_angle_to_hand_degrees':fold}
print(json.dumps(report,indent=2))
(HERE/'binding_diagnosis.json').write_text(json.dumps(report,indent=2))
