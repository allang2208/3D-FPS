"""Compare actual saved trouser fits and current routed lower-body poses."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageSetAudit20261019'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
inputs=read(R/'lower-combination-inputs.json')['rows'];poses=read(R/'source-movement-poses.json');base=read(P/'SourceAssets/BlueMageRobe20261018/Authored/Body/Jason.json');ref=base['bones'];scale=base['cloth_dimensions']['scale'];profile=read(P/'SourceAssets/BlueMageBoots20261019/boot_profile.json');cut=max(ref[n]['position'][2] for n in ('calf_l','calf_r'))+2*scale
def transform(points,bone,pose):
    local=(points-np.array(ref[bone]['position']))@np.array(ref[bone]['axes']).T;frame=pose[bone]
    return (local*np.array(frame['s']))@Rotation.from_quat(frame['q']).as_matrix().T+frame['p']
def distance(points,pose):
    nearest=np.full(len(points),1.e8)
    def capsule(bone,a,b,radius):
        nonlocal nearest
        a,b=transform(np.array([a,b]),bone,pose);ab=b-a;t=np.clip((points-a)@ab/max(float(ab@ab),1.e-10),0,1);nearest=np.minimum(nearest,np.linalg.norm(points-a-t[:,None]*ab,axis=1)-radius)
    for side in ('l','r'):
        k,a,t=[np.array(ref[n+'_'+side]['position']) for n in ('calf','foot','ball')];f=t-a;f[2]=0;f/=np.linalg.norm(f)
        capsule('calf_'+side,k,a,11.7)
        capsule('foot_'+side,a-f*3*scale-[0,0,5*scale],t+f*5*scale+[0,0,1.5*scale],9*scale)
        center=t+f*4*scale+[0,0,1.5*scale];capsule('ball_'+side,center,center,7*scale)
    return nearest
models=[];report=dict(scope='Saved mesh positions/weights and freshly sampled source gaits; not rendered Chaos/stair validation',trouser_fits={},rest={},clips={},failures=[])
for row in inputs:
    d=read(row['file']);p=np.array(d['positions']);indices=np.flatnonzero(p[:,2]<=cut)
    if row['kind']=='pants':
        q=p[(p[:,2]>=18)&(p[:,2]<=37.2)];z=q[:,2];fields=np.array(profile['fields']);cx,cy,rx,ry=[np.interp(z,profile['levels'],fields[:,i]) for i in range(4)];sign=np.where(q[:,0]>=0,1.,-1.);dx=sign*q[:,0]-cx;dy=q[:,1]-cy;angle=np.arctan2(dx,dy)
        inner=1/np.sqrt((np.sin(angle)/rx)**2+(np.cos(angle)/ry)**2)+.115*np.sin(z*2.05+np.sin(angle)*1.8)*np.exp(-((z-14)/4.6)**2)-.30
        gap=np.hypot(dx,dy)-inner;report['trouser_fits'][row['item']]=dict(vertices=len(q),outside=int((gap>.02).sum()),max_gap_cm=float(gap.max()))
        if (gap>.02).any():report['failures'].append('boot shaft fit '+row['item'])
    selected=indices[::max(1,math.ceil(len(indices)/1800))];selected=np.unique(np.r_[selected,indices[np.argmin(p[indices],axis=0)],indices[np.argmax(p[indices],axis=0)]])
    groups={}
    for oi,vi in enumerate(selected):
        for name,w in d['weights'][vi].items():
            ids,ws=groups.setdefault(name,([],[]));ids.append(oi);ws.append(w)
    for name,(ids,ws) in groups.items():
        ids=np.array(ids);b=d['bones'][name];groups[name]=(ids,np.array(ws)[:,None],(p[selected[ids]]-b['position'])@np.array(b['axes']).T)
    models.append(dict(name=row['item'],count=len(selected),groups=groups))
    gap=distance(p[indices],poses['reference']);report['rest'][row['item']]=dict(vertices=len(indices),outside=int((gap>0).sum()),max_gap_cm=float(gap.max()))
for key,clip in poses['clips'].items():
    row=dict(samples=len(clip['samples']),source=clip['path'],source_sha256=clip['asset_sha256'],outside_samples=0,max_gap_cm=-1.e8,worst_item='')
    for sample in clip['samples']:
        pose=sample['bones'];matrices={name:Rotation.from_quat(frame['q']).as_matrix().T for name,frame in pose.items()}
        for model in models:
            points=np.zeros((model['count'],3))
            for name,(ids,ws,local) in model['groups'].items():
                f=pose[name];points[ids]+=((local*f['s'])@matrices[name]+f['p'])*ws
            gap=distance(points,pose);worst=float(gap.max());row['outside_samples']+=int((gap>0).sum())
            if worst>row['max_gap_cm']:row['max_gap_cm']=worst;row['worst_item']=model['name']
    report['clips'][key]=row
    if row['outside_samples']:report['failures'].append('cloth collider containment '+key)
report['passed']=not report['failures'];(R/'lower-fit-and-motion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],fits=report['trouser_fits'],clips=len(report['clips']),poses=sum(c['samples'] for c in report['clips'].values()),failures=report['failures']),indent=2),flush=True)
