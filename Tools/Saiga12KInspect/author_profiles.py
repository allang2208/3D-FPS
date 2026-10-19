"""Fit only the Saiga support arm to each installed grip during shared inspection.

The shared gun/right-hand performance and clock are retained. Native local
finger poses come from the existing held pose; shoulder, elbow and forearm
follow the same contact, with the original segment lengths and skin calibration.
"""
import json,sys,copy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
from pose_math import matrix,rotation,pack,world,apply,role

ROOT=Path('D:/FPS3D/FPSGAME')
O=ROOT/'SourceAssets/Saiga12KInspect20261018'
sys.path.insert(0,str(ROOT/'SourceAssets/PKMLowpoly20260922/GripLayer56'))
import evaluate as arm_layer
AH=arm_layer.AH
d=json.loads((O/'Inputs/runtime-source.json').read_text())
contact_fits=json.loads((O/'Inputs/held-fit.json').read_text())
names=[b['name'] for b in d['bones']]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']}
rest={b['name']:matrix(b['world']) for b in d['bones']}
arm=AH.BONES
def is_left(n):
    return n in arm or (n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_')))
left=[n for n in names if is_left(n)]
fingers=[n for n in left if n not in arm]
base_idle={n:matrix(v) for n,v in d['idle'].items()}
base_world=world(base_idle,parents)
bind=SimpleNamespace(R=np.array([rotation(rest[n]) for n in arm]),st={},off={})
pos=np.array([rest[n][:3,3] for n in arm])
bind.U0=pos[4]-pos[1];bind.F0=pos[7]-pos[4]
bind.FL0=AH.frame(bind.F0,np.cross(bind.U0,bind.F0))
for i,origin,axis in ((2,pos[1],bind.U0),(3,pos[1],bind.U0),(5,pos[4],bind.F0),(6,pos[4],bind.F0)):
    bind.st[i]=(pos[i]-origin)@axis/(axis@axis)
    bind.off[i]=pos[i]-origin-bind.st[i]*axis

def sparse_track(n,values,times):
    values=np.asarray(values)
    # Quaternion signs are continuous before interpolation and key reduction.
    for i in range(1,len(values)):
        if values[i,3:7]@values[i-1,3:7]<0:values[i,3:7]*=-1
    identity=np.array([0,0,0,0,0,0,1,0,0,0.])
    if np.max(np.abs(values-identity))<1e-7:return None
    if np.max(np.abs(values-values[0]))<1e-7:
        return {'bone':n,'times':[0.],'values':values[0].tolist()}
    # A strict native-local tolerance keeps the contact path without an entire
    # duplicate sequence. This is production key reduction, not runtime IK.
    keys={0,len(times)-1};pending=[(0,len(times)-1)]
    while pending:
        a,b=pending.pop()
        if b-a<2:continue
        t=(times[a+1:b]-times[a])/(times[b]-times[a])
        interp=values[a][None,:]*(1-t[:,None])+values[b][None,:]*t[:,None]
        q=Slerp([0.,1.],Rot.from_quat(values[[a,b],3:7]))(t)
        pe=np.linalg.norm(interp[:,:3]-values[a+1:b,:3],axis=1)/.00002
        qe=(q.inv()*Rot.from_quat(values[a+1:b,3:7])).magnitude()/np.deg2rad(.015)
        se=np.linalg.norm(interp[:,7:]-values[a+1:b,7:],axis=1)/1e-6
        error=np.maximum.reduce([pe,qe,se]);i=int(np.argmax(error))
        if error[i]>1:
            k=a+1+i;keys.add(k);pending.extend(((a,k),(k,b)))
    keys=sorted(keys)
    return {'bone':n,'times':times[keys].tolist(),'values':values[keys].ravel().tolist()}

times=np.asarray([f['time'] for f in d['frames']])
report={'complete':False,'base':d['clip'],'duration':d['duration'],'families':{},'runtime_tested':False}
for family in ('base','angled','vertical','canted','prism'):
    profile=d['profiles'].get(family,{'family':'base','clips':[]})
    idle_layer=role(profile,'idle')
    if idle_layer and idle_layer['retained']:raise RuntimeError('Need actual retained idle: '+family)
    held=apply(base_idle,idle_layer,0.)
    held_world=world(held,parents)
    contact=np.linalg.inv(held_world['WPN_root'])@held_world['hand_l']
    fitted=contact_fits[family]
    smooth=lambda x:(lambda t:t*t*(3.-2.*t))(float(np.clip(x,0.,1.)))
    keys={n:[] for n in left+['ik_hand_l']}
    shoulder_shift=0.;hand_correction=0.
    for frame in d['frames']:
        contact_weight=smooth(frame['time']/.32)*smooth((d['duration']-frame['time'])/.45)
        original={n:matrix(v) for n,v in frame['local'].items()}
        local={n:m.copy() for n,m in original.items()}
        # Start with the family's own native local arm calibration. Outside
        # the support chain the shared performance remains byte-for-byte input.
        for n in left:
            b,f,s=pack(base_idle[n]),pack(held[n]),pack(original[n])
            s[:3]+=f[:3]-b[:3]
            s[3:7]=(Rot.from_quat(f[3:7])*Rot.from_quat(b[3:7]).inv()*Rot.from_quat(s[3:7])).as_quat()
            local[n]=matrix(s)
        for n in fingers:local[n]=held[n].copy()
        for n,value in fitted['finger_local'].items():
            q=Slerp([0.,1.],Rot.from_quat([pack(held[n])[3:7],value[3:7]]))([contact_weight]).as_matrix()[0]
            local[n][:3,:3]=q*np.linalg.norm(held[n][:3,:3],axis=0)
        pose=world(local,parents)
        target=pose['WPN_root']@contact
        target[:3,3]+=rotation(pose['WPN_root'])@np.asarray(fitted['palm_shift_root_cm'])*contact_weight
        rotations=np.array([rotation(pose[n]) for n in arm])
        points=np.array([pose[n][:3,3] for n in arm])
        max_reach=np.linalg.norm(points[4]-points[1])+np.linalg.norm(points[7]-points[4])-.3
        reach=target[:3,3]-points[1]
        shift=AH.unit(reach)*max(0.,np.linalg.norm(reach)-max_reach)
        points+=shift
        shoulder_shift=max(shoulder_shift,float(np.linalg.norm(shift)))
        pole=points[4]-points[1]
        # Calibrate the hinge construction against this exact native pose, so
        # a zero contact correction cannot change its existing twist helpers.
        zero_r,zero_p,_=arm_layer.layer_arm(rotations,points,rotations[7],points[7],0.,pole,bind,0.)
        out_r,out_p,info=arm_layer.layer_arm(rotations,points,rotation(target),target[:3,3],0.,pole,bind,0.)
        if info['short']>.001:raise RuntimeError('Unreachable support hand: '+family)
        hand_correction=max(hand_correction,float(np.linalg.norm(target[:3,3]-points[7])))
        desired={}
        for i,n in enumerate(arm):
            correction=out_r[i]@zero_r[i].T
            r=correction@rotations[i]
            p=out_p[i]+correction@(points[i]-zero_p[i])
            m=pose[n].copy();m[:3,:3]=r*np.linalg.norm(m[:3,:3],axis=0);m[:3,3]=p
            desired[n]=m
        desired['hand_l']=target
        # Reconstruct in actual hierarchy order, preserving all unmoved locals.
        final={}
        for n in names:
            parent=parents[n]
            if n in desired:
                final[n]=desired[n]
                local[n]=np.linalg.inv(final[parent])@final[n] if parent else final[n]
            else:final[n]=final[parent]@local[n] if parent else local[n]
        if 'ik_hand_l' in final:
            oldw=world(original,parents)
            final['ik_hand_l']=final['hand_l']@np.linalg.inv(oldw['hand_l'])@oldw['ik_hand_l']
            local['ik_hand_l']=np.linalg.inv(final[parents['ik_hand_l']])@final['ik_hand_l']
        for n in keys:
            a,b=pack(original[n]),pack(local[n])
            dq=(Rot.from_quat(b[3:7])*Rot.from_quat(a[3:7]).inv()).as_quat()
            value=np.r_[b[:3]-a[:3],dq,np.zeros(3)]
            if not np.isfinite(value).all():raise RuntimeError('Invalid native correction: '+n)
            keys[n].append(value)
    tracks=[t for n,v in keys.items() if (t:=sparse_track(n,v,times)) is not None]
    clips=[copy.deepcopy(c) for c in profile['clips'] if c['base']!=d['clip']]
    clips.append({'base':d['clip'],'duration':d['duration'],'retained':None,'tracks':tracks})
    (O/'Profiles'/('DA_'+family+'.json')).write_text(json.dumps({'family':family,'clips':clips}),encoding='utf-8')
    report['families'][family]={'tracks':len(tracks),'keys':sum(len(t['times']) for t in tracks),'held_hand_root_cm':(contact[:3,3]*100).tolist(),'fitted_palm_shift_root_cm':fitted['palm_shift_root_cm'],'contact_blend_in_seconds':.32,'contact_blend_out_seconds':.45,'maximum_hand_relocation_cm':hand_correction,'maximum_shoulder_reach_shift_cm':shoulder_shift,'other_clips_preserved':len(clips)-1}
    print('SAIGA_INSPECT_AUTHORED',family,report['families'][family],flush=True)
report['complete']=True
(O/'Receipts/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
