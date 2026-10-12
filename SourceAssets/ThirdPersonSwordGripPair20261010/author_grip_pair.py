"""Separate the complete support-hand grip, preserving the accepted blade/wrist frames."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SOURCE=ROOT/'SourceAssets/ThirdPersonSwordHandClearance20261010/candidate-actions.json'
helper=ROOT/'SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns={'__file__':str(helper)}
exec(compile(helper.read_text().split('clips={}')[0],str(helper),'exec'),ns)
data=json.loads(SOURCE.read_text())
fk,rot,unit=ns['fk'],ns['rot'],ns['unit']
a,b,c=ns['arms']['l'];l1,l2=ns['lengths']['l']
distance_down=2.4
clip=data['clips']['Overhead']
frames=np.array(clip['frames']);result=[];elbow_offsets=[];angular_changes=[]
for i,frame in enumerate(frames):
    w=fk(frame)
    weapon=ns['compose'](ns['compose'](w[ns['ix']['hand_r'],:7],ns['hand_to_weapon']),
        np.r_[0.,0.,0.,ns['axis']([0,0,1],-math.radians(clip['curves']['SwordGripRoll'][i]))])
    target=w[c,:7].copy()
    target[:3]+=rot(weapon[3:7],np.array([0.,0.,-distance_down]))
    A=w[a,:3];C=target[:3];ray=unit(C-A);distance=np.linalg.norm(C-A)
    if not abs(l1-l2)+.01 < distance < l1+l2-.01:
        raise RuntimeError('Separated grip is outside the original left-arm reach at frame '+str(i))
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    # Closest elbow on the new reach circle. Keep the accepted hemisphere and
    # wrist orientation; no new grip-roll or elbow-pole search is performed.
    pole=unit(w[b,:3]-A-ray*np.dot(w[b,:3]-A,ray))
    elbow=A+ray*along+pole*math.sqrt(max(0.,l1*l1-along*along))
    revised=frame.copy()
    ns['fit'](revised,w,'l',target,elbow)
    elbow_offsets.append(float(np.linalg.norm(elbow-w[b,:3])))
    result.append(revised.tolist())
for take in data['clips'].values():take['frames']=result
data['provenance']+='; support hand translated 2.4 cm toward pommel, nearest accepted elbow plane'
data['accepted_arms_sha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report={
    'authoring_only':True,
    'source':str(SOURCE),
    'source_sha256':data['accepted_arms_sha256'],
    'left_grip_slide_cm':distance_down,
    'axial_wrist_spacing_cm':10.+distance_down,
    'max_elbow_follow_cm':max(elbow_offsets),
    'preserved':'right arm and hand, blade path, left wrist world orientation, all other body tracks, bone lengths, finger pose and timing',
    'changed':'left upperarm/lowerarm/hand local rotations and their twist/corrective roots',
    'rate':clip['rate'], 'frame_count':len(result)
}
(OUT/'candidate-actions.json').write_text(json.dumps(data,separators=(',',':')))
(OUT/'pair-authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
