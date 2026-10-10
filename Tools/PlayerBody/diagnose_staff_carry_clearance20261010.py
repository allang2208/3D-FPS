"""Scoped offline diagnosis: shaft/body envelopes across actual gait samples.

This is geometric pose evidence, not an in-game or visual acceptance result.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffCarryClearance20261010'
data=json.loads((OUT/'authored.json').read_text())
old=json.loads((ROOT/'SourceAssets/ThirdPersonStaffMotifect20261010/authored.json').read_text())
target=json.loads((ROOT/'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
gaits=json.loads((OUT/'gaits.json').read_text())
names=data['names'];ix={n:i for i,n in enumerate(names)};parents=target['parents']
def arm_indices(side):
    indices=[];root=ix['clavicle_'+side];hand=ix['hand_'+side]
    for i in range(len(names)):
        b=i
        while b>=0:
            if b==hand and i!=hand:break
            if b==root:indices.append(i);break
            b=parents[b]
    return indices
right=arm_indices('r');left=arm_indices('l')
def fk(f):
    p=f[:,:,:3].copy();q=R.from_quat(f[:,:,3:7].reshape(-1,4)).as_matrix().reshape(*f.shape[:2],3,3)
    scale=f[:,:,7:].copy()
    for i,b in enumerate(parents):
        if b>=0:
            p[:,i]=p[:,b]+np.einsum('nij,nj->ni',q[:,b],p[:,i]*scale[:,b])
            q[:,i]=q[:,b]@q[:,i];scale[:,i]*=scale[:,b]
    return p,q
def point_segment(p,a,b):
    v=b-a;t=np.clip(np.sum((p-a)*v,axis=-1)/np.maximum(np.sum(v*v,axis=-1),1e-12),0,1)
    return np.linalg.norm(p-a-t[...,None]*v,axis=-1)
def segments(a,b,c,d):
    u=b-a;v=d-c;w=a-c
    aa=np.sum(u*u,axis=-1);bb=np.sum(u*v,axis=-1);cc=np.sum(v*v,axis=-1)
    dd=np.sum(u*w,axis=-1);ee=np.sum(v*w,axis=-1);det=aa*cc-bb*bb
    den=np.where(abs(det)<1e-8,1,det)
    s=(bb*ee-cc*dd)/den;t=(aa*ee-bb*dd)/den
    interior=np.where((abs(det)>1e-8)&(s>=0)&(s<=1)&(t>=0)&(t<=1),np.linalg.norm(w+s[:,None]*u-t[:,None]*v,axis=-1),np.inf)
    return np.minimum.reduce([interior,point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b)])
body=[('pelvis','spine_05',20.),('head','head',12.)]
for side in ['r','l']:
    body.extend([(f'thigh_{side}',f'calf_{side}',11.),(f'calf_{side}',f'foot_{side}',8.)])
mount=np.array(data['staff_mount']);mq=R.from_quat(mount[3:7]).as_matrix()
book=np.array(data['clips']['Staff.BookCarry']['frames'][0])
bm=np.array(data['book_mount']);bq=R.from_quat(bm[3:7]).as_matrix()
report={'kind':'offline geometric envelope diagnosis; no game acceptance','gaits':{},'runtime_tested':False}
for key,gait in gaits.items():
    row={}
    for label,source in [('before',old),('after',data)]:
        carry=np.array(source['clips']['Staff.NativeArm.Carry']['frames'])
        f=np.repeat(np.array(gait['frames']),len(carry),axis=0)
        f[:,right]=np.tile(carry[:,right],(len(gait['frames']),1,1))
        if label=='after':
            alpha=.06 if '.Jog.' in key else .10
            live=f[:,left].copy();base=np.broadcast_to(book[left],live.shape).copy()
            mixed=base*(1-alpha)+live*alpha
            liveq=np.where(np.sum(base[:,:,3:7]*live[:,:,3:7],axis=-1,keepdims=True)<0,-live[:,:,3:7],live[:,:,3:7])
            mixed[:,:,3:7]=base[:,:,3:7]*(1-alpha)+liveq*alpha
            mixed[:,:,3:7]/=np.linalg.norm(mixed[:,:,3:7],axis=-1,keepdims=True)
            f[:,left]=mixed
            # Match the runtime whole-arm support frame: shoulder position
            # follows gait; authored complete arm orientation is retained.
            _,liveq=fk(f);_,sourceq=fk(np.tile(carry,(len(gait['frames']),1,1)))
            upper=ix['upperarm_r'];parent=parents[upper]
            chest=parents[parent]
            delta=liveq[:,chest]@np.swapaxes(sourceq[:,chest],1,2)
            yaw=np.arctan2(-delta[:,0,1],delta[:,1,1])
            heading=R.from_rotvec(np.column_stack([yaw*0,yaw*0,yaw])).as_matrix()
            f[:,upper,3:7]=R.from_matrix(np.swapaxes(liveq[:,parent],1,2)@heading@sourceq[:,upper]).as_quat()
        p,q=fk(f);h=ix['hand_r'];origin=p[:,h]+np.einsum('nij,j->ni',q[:,h],mount[:3]);axis=(q[:,h]@mq)[:,:,2]
        start=origin-axis*80.;end=origin+axis*62.
        distances={f'{a}:{b}':float(np.min(segments(start,end,p[:,ix[a]],p[:,ix[b]])-radius-5.)) for a,b,radius in body}
        row[label]={'minimum_shaft_envelope_clearance_cm':min(distances.values()),'per_body_segment_cm':distances,
                    'samples':len(f),'right_wrist_x_range_cm':[float(p[:,h,0].min()),float(p[:,h,0].max())]}
        worst=min(body,key=lambda ab:distances[f'{ab[0]}:{ab[1]}'])
        wi=int(np.argmin(segments(start,end,p[:,ix[worst[0]]],p[:,ix[worst[1]]])-worst[2]-5.))
        row[label]['worst']={'gait_frame':wi//len(carry),'carry_frame':wi%len(carry),'body':worst[:2],
            'shoulder':p[wi,ix['upperarm_r']].tolist(),'hand':p[wi,h].tolist(),'shaft_start':start[wi].tolist(),'shaft_end':end[wi].tolist(),
            'body_start':p[wi,ix[worst[0]]].tolist(),'body_end':p[wi,ix[worst[1]]].tolist()}
        if label=='after':
            lh=ix['hand_l'];origin=p[:,lh]+np.einsum('nij,j->ni',q[:,lh],bm[:3]);rotation=q[:,lh]@bq
            distances={}
            for a,b,radius in body:
                points=p[:,ix[a],None,:]+(p[:,ix[b]]-p[:,ix[a]])[:,None,:]*np.linspace(0,1,65)[None,:,None]
                local=np.einsum('nji,nkj->nki',rotation,points-origin[:,None,:])
                box=np.clip(local,[0.,-12.093005,-2.850003],[15.51885,12.093005,2.850003])
                distances[f'{a}:{b}']=float(np.min(np.linalg.norm(local-box,axis=-1))-radius)
            row[label]['book_envelope_clearance_cm']=min(distances.values())
            row[label]['book_per_body_segment_cm']=distances
    report['gaits'][key]=row
(OUT/'clearance-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for key,row in report['gaits'].items():
    print(key,'shaft before/after',round(row['before']['minimum_shaft_envelope_clearance_cm'],2),round(row['after']['minimum_shaft_envelope_clearance_cm'],2),
          'book',round(row['after']['book_envelope_clearance_cm'],2))
