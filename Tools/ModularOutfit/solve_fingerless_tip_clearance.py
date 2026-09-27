"""Minimal distal-finger relaxation against the leather; keep wrist/arm/grip roots."""
import json,math,hashlib,os,copy
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';O=R/'ClearanceReview';OUT=R/'FingerClearance';OUT.mkdir(exist_ok=True)
ns={};exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
read=ns['read'];prepare=ns['prepare'];deform=ns['deform'];matrix=ns['matrix'];tree=ns['tree']
def rotation(axis,angle):
    axis=np.asarray(axis);x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);a=math.radians(angle)
    return np.eye(3)+math.sin(a)*K+(1-math.cos(a))*(K@K)
def score(points,faces,gp,gt,gbvh):
    pairs=tree(points,faces).overlap(gbvh)
    if not pairs:return 0.,None
    ix=np.asarray(pairs);a=points[faces[ix[:,0]]];b=gp[gt[ix[:,1]]]
    an=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
    an/=np.maximum(np.linalg.norm(an,axis=1)[:,None],1e-15);bn/=np.maximum(np.linalg.norm(bn,axis=1)[:,None],1e-15)
    da=np.einsum('nki,ni->nk',a-b[:,0,None,:],bn);db=np.einsum('nki,ni->nk',b-a[:,0,None,:],an)
    depths=np.minimum.reduce([-da.min(1),da.max(1),-db.min(1),db.max(1)])
    i=int(np.argmax(depths));return float(max(0,depths[i])),-bn[i]
prior=read(OUT/'manifest.json') if (OUT/'manifest.json').exists() else []
retry=os.environ.get('FINGERLESS_RETRY_FAILED')=='1'
failed={v['asset'] for v in prior if v['remaining_sample_cross_mm']>.05}
manifest=[v for v in prior if v['asset'] not in failed] if retry else []
for name in ('PKM','A762'):
    sd=read(R/'SkinCoverage'/(name+'_review.json'));gd=read(R/'Authored'/(name+'.json'));s=prepare(sd,True);g=prepare(gd)
    bone_groups={bn:(ids,w,local) for bn,ids,w,local in s['groups']}
    # The scan identified distal pinkies pressing through the palm. Restrict
    # the correction to these end joints; all grip roots and other fingers stay.
    fingers=[f'{finger}_02_{side}' for finger in ('pinky','ring','middle','thumb','index') for side in ('l','r') if f'{finger}_02_{side}' in bone_groups]
    for file in sorted(O.glob(name+'__*_poses.json')):
        d=read(file)
        if retry and d['asset'] not in failed:continue
        needs={bn:[] for bn in fingers};axes={};frame_axes={bn:[] for bn in fingers};before_max=0.;unresolved=0.
        for pose in d['poses']:
            bones=pose['bones'];sp=deform(s,bones);gp=deform(g,bones);gbvh=tree(gp,g['t'])
            for bn in fingers:
                child=bn.replace('_02_','_03_');related=[n for n in (bn,child) if n in bone_groups]
                ids=np.unique(np.concatenate([bone_groups[n][0] for n in related]));mask=np.zeros(len(sp),dtype=bool);mask[ids]=True;faces=s['t'][mask[s['t']].any(1)]
                initial,outward=score(sp,faces,gp,g['t'],gbvh);before_max=max(before_max,initial)
                chosen=0.;best=initial;chosen_axis=np.array([0.,0.,1.])
                if initial>.003:
                    bm=matrix(bones[bn]);tip=matrix(bones[child])[:3,3]-bm[:3,3]
                    if bn not in axes or retry:
                        target=np.cross(tip,outward);local_axis=np.linalg.inv(bm[:3,:3])@target
                        axis=local_axis/max(np.linalg.norm(local_axis),1e-12);axes[bn]=axis
                    axis=axes[bn]
                    angles=[a for n in range(2,33,2) for a in ((n,-n) if retry else (n,))]
                    for angle in angles:
                        changed=bm.copy();changed[:3,:3]=bm[:3,:3]@rotation(axis,angle);delta=changed@np.linalg.inv(bm)
                        candidate=sp.copy();candidate_gp=gp.copy()
                        for nn,ii,ww,ll in s['groups']:
                            if nn not in related:continue
                            before=matrix(bones[nn]);after=delta@before
                            candidate[ii]+=((ll@after.T)[:,:3]-(ll@before.T)[:,:3])*ww[:,None]
                        for nn,ii,ww,ll in g['groups']:
                            if nn not in related:continue
                            before=matrix(bones[nn]);after=delta@before
                            candidate_gp[ii]+=((ll@after.T)[:,:3]-(ll@before.T)[:,:3])*ww[:,None]
                        depth,_=score(candidate,faces,candidate_gp,g['t'],tree(candidate_gp,g['t']))
                        if depth<best:best=depth;chosen=float(abs(angle));chosen_axis=axis*(1 if angle>=0 else -1)
                        if depth<.001:chosen=float(abs(angle));chosen_axis=axis*(1 if angle>=0 else -1);best=depth;break
                unresolved=max(unresolved,best);needs[bn].append(chosen);frame_axes[bn].append(chosen_axis.tolist())
        corrections={}
        for bn,values in needs.items():
            if max(values)==0:continue
            # Smooth contact envelopes ramp in/out over 0.2 seconds. Never
            # reduce the required angle at a sampled contact point.
            times=np.array([p['time'] for p in d['poses']]);v=np.array(values);envelope=np.zeros_like(v);envelope_axes=np.tile([0.,0.,1.],(len(v),1))
            for i,a in enumerate(v):
                if a==0:continue
                t=np.clip(1-abs(times-times[i])/.20,0,1);smooth=t*t*t*(10+t*(-15+6*t));replace=a*smooth>envelope;envelope_axes[replace]=frame_axes[bn][i];envelope=np.maximum(envelope,a*smooth)
            corrections[bn]=dict(axis=axes[bn].tolist(),axes=envelope_axes.tolist(),angles=envelope.tolist())
        if corrections:
            disk=P/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')
            record=dict(profile=name,label=d['label'],asset=d['asset'],source_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),times=[p['time'] for p in d['poses']],corrections=corrections,
                before_cross_mm=before_max*10,remaining_sample_cross_mm=unresolved*10,max_angle=max(max(v['angles']) for v in corrections.values()),unchanged='wrist, arms, finger roots, other fingers, positions, scales, timing')
            (OUT/(name+'__'+d['label']+'.json')).write_text(json.dumps(record,indent=2));manifest.append({k:v for k,v in record.items() if k not in ('corrections','times')})
            print('FINGER_TIP_RELAX',name,d['label'],round(before_max*10,3),round(unresolved*10,3),record['max_angle'],flush=True)
            if os.environ.get('FINGERLESS_SOLVE_LIMIT') and len(manifest)>=int(os.environ['FINGERLESS_SOLVE_LIMIT']):
                print('LIMITED_PROBE_COMPLETE');raise SystemExit(0)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('FINGER_TIP_SOLVED',len(manifest),flush=True)
