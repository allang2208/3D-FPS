"""Open the reload thumb away from the sleeve while leaving the gripping fingers fixed."""
import json,math,hashlib,os
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';O=R/'ClearanceReview';C=R/'CuffThumbClearance';C.mkdir(exist_ok=True);ns={}
exec((P/'Tools/ModularOutfit/solve_fingerless_tip_clearance.py').read_text().split('prior=')[0],ns)
ns['measure']=ns['ns']['measure']
sd=ns['read'](O/'A762_shirt.json');p=np.asarray(sd['positions']);t=np.asarray(sd['triangles']);near=np.linalg.norm(p[t].mean(1)-np.asarray(sd['bones']['hand_r']['position']),axis=1)<12;sd['triangles']=t[near].tolist();sleeve=ns['prepare'](sd);s=ns['prepare'](ns['read'](A/'A762_skin.json'),True);g=ns['prepare'](ns['read'](A/'A762_glove.json'));bn='thumb_01_r';related=('thumb_01_r','thumb_02_r','thumb_03_r');manifest=[]
def evaluate(bones):
    gp=ns['deform'](g,bones);return max(ns['measure'](sleeve,g,ns['deform'](sleeve,bones),gp)['max_plane_cross_mm'],ns['measure'](s,g,ns['deform'](s,bones),gp)['max_plane_cross_mm'])
def change(bones,axis,angle):
    bm=ns['matrix'](bones[bn]);after=bm.copy();after[:3,:3]=bm[:3,:3]@ns['rotation'](axis,angle);delta=after@np.linalg.inv(bm);result=dict(bones)
    for n in related:
        m=delta@ns['matrix'](bones[n]);result[n]=dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
    return result
files=sorted(A.glob('A762__*_poses.json'))
if os.environ.get('FINGERLESS_ARM_PROBE')=='1':files=[A/'A762__base_reload_empty_poses.json']
for f in files:
    d=ns['read'](f);values=[];axes=[];worst=0.;initialmax=0.
    for pose in d['poses']:
        initial=evaluate(pose['bones']);initialmax=max(initialmax,initial);best=initial;chosen=0.;axis=[0.,0.,1.]
        if initial>.03:
            for angle,direction in [(a,np.array([0.,math.cos(t),math.sin(t)])) for a in (2,4,6,8,10,12,16,20,25,30) for t in np.arange(0,2*math.pi,math.pi/4)]:
                depth=evaluate(change(pose['bones'],direction,angle))
                if depth<best:best=depth;chosen=angle;axis=direction.tolist()
                if depth<=.005:break
        worst=max(worst,best);values.append(chosen);axes.append(axis)
    if initialmax<=.03:continue
    print('THUMB_CUFF_SOLVE',d['label'],initialmax,worst,max(values),flush=True)
    if worst>.03:continue
    times=np.asarray([p['time'] for p in d['poses']]);raw=np.asarray(values);angles=raw.copy();eax=np.asarray(axes)
    for i,v in enumerate(raw):
        ramp=np.clip(1-abs(times-times[i])/.20,0,1);ease=ramp*ramp*ramp*(10+ramp*(-15+6*ramp));replace=v*ease>angles;angles[replace]=v*ease[replace];eax[replace]=axes[i]
    remaining=max(evaluate(change(pose['bones'],eax[i],angles[i])) for i,pose in enumerate(d['poses']))
    record=dict(profile='A762',label=d['label'],asset=d['asset'],source_sha256=hashlib.sha256((P/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),times=times.tolist(),corrections={bn:dict(axis=[0.,0.,1.],axes=eax.tolist(),angles=angles.tolist())},remaining_sample_cross_mm=remaining,max_angle=float(max(angles)))
    (C/('A762__'+d['label']+'.json')).write_text(json.dumps(record,indent=2));manifest.append({k:v for k,v in record.items() if k not in ('times','corrections')});print('THUMB_CUFF_SMOOTH',d['label'],remaining,flush=True)
(C/'manifest.json').write_text(json.dumps(manifest,indent=2))
