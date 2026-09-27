"""Relax the remaining A762 right middle fingertip from the saved compressed poses."""
import json,math,hashlib,copy
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';C=R/'SavedFingerRefinement';C.mkdir(exist_ok=True);ns={}
exec((P/'Tools/ModularOutfit/solve_fingerless_tip_clearance.py').read_text().split('prior=')[0],ns)
s=ns['prepare'](ns['read'](A/'A762_skin.json'),True);g=ns['prepare'](ns['read'](A/'A762_glove.json'));report=ns['read'](A/'clearance-full.json');manifest=[]
bn='middle_03_r'
for row in report['poses']:
    if max(v['max_plane_cross_mm'] for v in row['samples'])<=.03:continue
    if row['profile']!='A762':raise RuntimeError('Unexpected residual profile')
    d=ns['read'](A/('A762__'+row['label']+'_poses.json'));times=np.asarray([p['time'] for p in d['poses']]);angles=[];axes=[];remaining=0.
    for pose in d['poses']:
        bones=pose['bones'];sp=ns['deform'](s,bones);gp=ns['deform'](g,bones);initial,_=ns['score'](sp,s['t'],gp,g['t'],ns['tree'](gp,g['t']));best=initial;chosen=0.;chosen_axis=[0.,0.,1.]
        if initial>.003:
            bm=ns['matrix'](bones[bn]);ii,ww,ll=next((ii,ww,ll) for nn,ii,ww,ll in s['groups'] if nn==bn)
            for angle,axis in [(a,np.array([0.,math.cos(t),math.sin(t)])) for a in (1.,2.,3.,4.,6.,8.,10.,12.) for t in np.arange(0,2*math.pi,math.pi/4)]:
                after=bm.copy();after[:3,:3]=bm[:3,:3]@ns['rotation'](axis,angle);candidate=sp.copy();candidate[ii]+=((ll@after.T)[:,:3]-(ll@bm.T)[:,:3])*ww[:,None]
                depth,_=ns['score'](candidate,s['t'],gp,g['t'],ns['tree'](gp,g['t']))
                if depth<best:best=depth;chosen=angle;chosen_axis=axis.tolist()
                if depth<.0005:break
        angles.append(chosen);axes.append(chosen_axis);remaining=max(remaining,best*10)
    v=np.asarray(angles);envelope=v.copy();eax=np.asarray(axes)
    for i,a in enumerate(v):
        t=np.clip(1-abs(times-times[i])/.15,0,1);ease=t*t*t*(10+t*(-15+6*t));replace=a*ease>envelope;eax[replace]=axes[i];envelope=np.maximum(envelope,a*ease)
    record=dict(profile='A762',label=d['label'],asset=d['asset'],source_sha256=hashlib.sha256((P/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),times=times.tolist(),corrections={bn:dict(axis=[0.,0.,1.],axes=eax.tolist(),angles=envelope.tolist())},remaining_sample_cross_mm=remaining,max_angle=float(max(v)))
    if remaining>.03:raise RuntimeError('Unresolved '+d['label']+' '+str(remaining))
    (C/('A762__'+d['label']+'.json')).write_text(json.dumps(record,indent=2));manifest.append({k:v for k,v in record.items() if k not in ('corrections','times')});print('SAVED_POSE_REFINEMENT',d['label'],record['max_angle'],remaining,flush=True)
(C/'manifest.json').write_text(json.dumps(manifest,indent=2))
