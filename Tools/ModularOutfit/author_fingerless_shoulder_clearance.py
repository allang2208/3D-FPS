"""Blend a fixed-hand shoulder/elbow solution through the two folded A762 reload poses."""
import json,hashlib,math,numpy as np
from pathlib import Path
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';C=R/'CuffShoulderClearance';C.mkdir(exist_ok=True);ns={}
exec((P/'Tools/ModularOutfit/probe_fingerless_shoulder_clearance.py').read_text().split('results=[]')[0],ns)
mx=ns['mx'];parents=ns['parents'];manifest=[]
for f in sorted(A.glob('A762__*_poses.json')):
    d=json.loads(f.read_text());poses=d['poses'];initial=[ns['thumb']['evaluate'](p['bones']) for p in poses]
    if max(initial)<=.03:continue
    if len(poses)!=66:raise RuntimeError('Unexpected reload curve '+d['label'])
    times=np.asarray([p['time'] for p in poses]);clavicle=np.zeros(len(poses));elbow=np.zeros(len(poses))
    for i,c,e in [(44,30.,-60.),(45,5.,-60.)]:
        t=np.clip(1-abs(times-times[i])/.20,0,1);ease=t*t*t*(10+t*(-15+6*t));clavicle=np.maximum(clavicle,c*ease);elbow=np.minimum(elbow,e*ease)
    corrections={bn:dict(axis=[0.,0.,1.],axes=[],angles=[]) for bn in ('clavicle_r','upperarm_r','lowerarm_r','hand_r')};worst=0.;hand_error=0.;corrected=[]
    for i,p in enumerate(poses):
        before=p['bones'];after=ns['solve'](before,[0,1,0],clavicle[i],elbow[i]);worst=max(worst,ns['thumb']['evaluate'](after));hand_error=max(hand_error,float(np.linalg.norm(mx(before['hand_r'])-mx(after['hand_r']))));corrected.append(dict(time=p['time'],bones=after))
        for bn,c in corrections.items():
            parent=parents[bn];b=np.linalg.inv(mx(before[parent]))@mx(before[bn]);a=np.linalg.inv(mx(after[parent]))@mx(after[bn]);q=Matrix((np.linalg.inv(b[:3,:3])@a[:3,:3]).tolist()).to_quaternion()
            if q.w<0:q.negate()
            c['angles'].append(math.degrees(q.angle));c['axes'].append(list(q.axis))
    record=dict(profile='A762',label=d['label'],asset=d['asset'],source_sha256=hashlib.sha256((P/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),times=times.tolist(),corrections=corrections,remaining_sample_cross_mm=worst,max_angle=max(max(c['angles']) for c in corrections.values()),world_hand_transform_error=hand_error)
    (C/('A762__'+d['label']+'.json')).write_text(json.dumps(record,indent=2));manifest.append({k:v for k,v in record.items() if k not in ('times','corrections')});(C/('A762__'+d['label']+'_poses.json')).write_text(json.dumps(dict(d,poses=corrected),separators=(',',':')));print('SHOULDER_CUFF_CANDIDATE',d['label'],worst,hand_error,flush=True)
(C/'manifest.json').write_text(json.dumps(manifest,indent=2))
