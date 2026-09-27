"""Compare the saved corrected wrist against the original grip anchor samples."""
import json,math
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';O=R/'ClearanceReview';rows=[]
for f in sorted(A.glob('*__*_poses.json')):
    new=json.loads(f.read_text());old=json.loads((O/f.name).read_text());points=[];rotations=[]
    for p,before in zip(new['poses'],old['poses']):
        a=p['bones']['hand_r'];b=before['bones']['hand_r'];points.append(float(np.linalg.norm(np.asarray(a['position'])-b['position'])*10));ma=np.asarray(a['axes']).T;mb=np.asarray(b['axes']).T;ma/=np.linalg.norm(ma,axis=0);mb/=np.linalg.norm(mb,axis=0);r=ma@mb.T;rotations.append(math.degrees(math.acos(np.clip((np.trace(r)-1)*.5,-1,1))))
    rows.append(dict(profile=new['profile'],label=new['label'],max_position_mm=max(points),max_rotation_degrees=max(rotations)))
(A/'hand-contact-check.json').write_text(json.dumps(rows,indent=2))
print('RIGHT_HAND_ANCHOR',max(r['max_position_mm'] for r in rows),max(r['max_rotation_degrees'] for r in rows))
for r in rows:
    if r['max_position_mm']>1 or r['max_rotation_degrees']>.2:print('CONTACT_DRIFT',r)
