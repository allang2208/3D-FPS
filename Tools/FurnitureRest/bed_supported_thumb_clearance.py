"""Lift only the lower-bunk reach through its subframe blanket contact."""
import copy,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9'
ns={'__file__':str(ROOT/'Tools/FurnitureRest/bed_supported_v9.py')}
exec((ROOT/'Tools/FurnitureRest/bed_supported_v9.py').read_text().rsplit('for kind in kinds:',1)[0],ns)
fk,ix,ik,rot,smooth=[ns[k] for k in ('fk','ix','ik','rot','smooth')]
data=json.loads((OUT/'authored.json').read_text())
original=OUT/'authored.pre-thumb-clearance.json'
if not original.exists():original.write_bytes((OUT/'authored.json').read_bytes())
base=json.loads(original.read_text());changed=[]
for kind,start,duration,amplitude,sides in [('Bunk',.55,.8,1.3,('l','r')),('Ward',3.95,.8,1.5,('l',))]:
    role=f'Rest.{kind}.Enter';frames=[]
    for j,frame in enumerate(base['clips'][role]['frames']):
        f=np.array(frame);t=j/30;lift=amplitude*math.sin(math.pi*smooth((t-start)/duration))**2
        if lift>1e-8:
            for side in sides:
                w=fk(f);hand=ix['hand_'+side];elbow=ix['lowerarm_'+side]
                ik(f,side,('upperarm','lowerarm','hand'),w[hand,:3,3]+[0,0,lift],w[elbow,:3,3])
                rot(f,hand,w[hand,:3,:3])
        frames.append(f.tolist())
    if np.array_equal(np.array(data['clips'][role]['frames']),np.array(frames)):continue
    data['clips'][role]['frames']=frames
    data['clips'][f'Rest.{kind}.Exit']['frames']=copy.deepcopy(frames[::-1])+[copy.deepcopy(frames[0]) for _ in range(9)]
    changed.extend([role,f'Rest.{kind}.Exit'])
data['changed_roles']=changed
(OUT/'authored.json').write_text(json.dumps(data,separators=(',',':')))
print('BED_THUMB_CLEARANCE_AUTHORED',changed)
