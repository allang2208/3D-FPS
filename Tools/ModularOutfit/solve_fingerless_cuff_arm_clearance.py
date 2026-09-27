"""Move the elbow around the fixed shoulder/wrist axis, retaining hand and weapon contact."""
import json,math,hashlib,copy,os
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';A=R/'ClearanceAfter';O=R/'ClearanceReview';C=R/'CuffArmClearance';C.mkdir(exist_ok=True);ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
def mx(b):return ns['matrix'](b)
def pack(m):return dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
def between(a,b):return np.asarray(Vector(a).rotation_difference(Vector(b)).to_matrix())
def orbit(bones,angle,parents):
    upper=mx(bones['upperarm_r']);lower=mx(bones['lowerarm_r']);hand=mx(bones['hand_r']);shoulder=upper[:3,3];wrist=hand[:3,3];elbow=lower[:3,3];axis=wrist-shoulder;axis/=np.linalg.norm(axis)
    rot=np.asarray(Matrix.Rotation(math.radians(angle),3,Vector(axis)));target=shoulder+rot@(elbow-shoulder)
    ru=between(elbow-shoulder,target-shoulder);rl=between(wrist-elbow,wrist-target)
    du=np.eye(4);du[:3,:3]=ru;du[:3,3]=shoulder-ru@shoulder;dl=np.eye(4);dl[:3,:3]=rl;dl[:3,3]=target-rl@elbow
    result={}
    for bn,b in bones.items():
        chain=[];n=bn
        while n in parents:chain.append(n);n=parents[n]
        transform=np.eye(4) if 'hand_r' in chain else dl if 'lowerarm_r' in chain else du if 'upperarm_r' in chain else np.eye(4)
        result[bn]=pack(transform@mx(b))
    return result
manifest=[]
for name in ((os.environ['FINGERLESS_ARM_PROFILE'],) if os.environ.get('FINGERLESS_ARM_PROFILE') else ('PKM','A762')):
    sd=ns['read'](O/(name+'_shirt.json'));gd=ns['read'](A/(name+'_glove.json'));skin=ns['read'](A/(name+'_skin.json'));s=ns['prepare'](skin,True);g=ns['prepare'](gd)
    points=np.asarray(sd['positions']);tri=np.asarray(sd['triangles']);center=points[tri].mean(1);near=np.minimum.reduce([np.linalg.norm(center-np.asarray(sd['bones']['hand_'+side]['position']),axis=1) for side in ('l','r')])<12;sd['triangles']=tri[near].tolist();sleeve=ns['prepare'](sd)
    ids={b['index']:n for n,b in gd['bones'].items()};parents={n:ids.get(b['parent']) for n,b in gd['bones'].items()}
    files=sorted(A.glob(name+'__*_poses.json'))
    if os.environ.get('FINGERLESS_ARM_PROBE')=='1':files=[A/(name+'__'+('base_reload' if name=='PKM' else 'base_reload_empty')+'_poses.json')]
    def evaluate(bones):
        gp=ns['deform'](g,bones);a=ns['measure'](sleeve,g,ns['deform'](sleeve,bones),gp)['max_plane_cross_mm'];b=ns['measure'](s,g,ns['deform'](s,bones),gp)['max_plane_cross_mm'];return max(a,b)
    for f in files:
        d=ns['read'](f);times=np.asarray([p['time'] for p in d['poses']]);values=[];before=0.;worst=0.
        for pose in d['poses']:
            initial=evaluate(pose['bones']);before=max(before,initial);best=initial;chosen=0.
            if initial>.03:
                for angle in [a for n in (2,4,6,8,10,12,16,20,25,30,40,50,60,75,90,120,150,180) for a in (n,-n)]:
                    depth=evaluate(orbit(pose['bones'],angle,parents))
                    if depth<best:best=depth;chosen=angle
                    if depth<=.005:break
            values.append(chosen);worst=max(worst,best)
        print('CUFF_ARM_SOLVE',name,d['label'],before,worst,min(values),max(values),flush=True)
        if before<=.03:continue
        if worst>.03:continue
        raw=np.asarray(values);angles=raw.copy()
        for i,v in enumerate(raw):
            if not v:continue
            ramp=np.clip(1-abs(times-times[i])/.2,0,1);ease=ramp*ramp*ramp*(10+ramp*(-15+6*ramp));replace=abs(v)*ease>abs(angles);angles[replace]=v*ease[replace]
        corrections={bn:dict(axis=[0.,0.,1.],axes=[],angles=[]) for bn in ('upperarm_r','lowerarm_r','hand_r')};remaining=0.
        for i,pose in enumerate(d['poses']):
            before_bones=pose['bones'];after_bones=orbit(before_bones,angles[i],parents);remaining=max(remaining,evaluate(after_bones))
            for bn,c in corrections.items():
                parent=parents[bn];local0=np.linalg.inv(mx(before_bones[parent]))@mx(before_bones[bn]);local1=np.linalg.inv(mx(after_bones[parent]))@mx(after_bones[bn]);q=Matrix((np.linalg.inv(local0[:3,:3])@local1[:3,:3]).tolist()).to_quaternion()
                if q.w<0:q.negate()
                c['angles'].append(math.degrees(q.angle));c['axes'].append(list(q.axis))
        record=dict(profile=name,label=d['label'],asset=d['asset'],source_sha256=hashlib.sha256((P/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),times=times.tolist(),corrections=corrections,remaining_sample_cross_mm=remaining,max_angle=max(max(c['angles']) for c in corrections.values()),max_elbow_orbit_degrees=max(abs(angles)),before_cross_mm=before)
        (C/(name+'__'+d['label']+'.json')).write_text(json.dumps(record,indent=2));manifest.append({k:v for k,v in record.items() if k not in ('times','corrections')});print('CUFF_ARM_SMOOTH',name,d['label'],remaining,flush=True)
(C/'manifest.json').write_text(json.dumps(manifest,indent=2))
