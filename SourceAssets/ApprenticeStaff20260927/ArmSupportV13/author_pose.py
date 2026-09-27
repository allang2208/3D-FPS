"""Bow support grasp -> native right staff hand, complete authored arm poses.

UE centimetres, proper rotations, no negative-scale skeletal mirror. Contact
fitting uses named skin pad patches; native bone translations remain unchanged.
This is production fitting and pose export, not visual/runtime acceptance.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares

P=Path(__file__).resolve().parent; ROOT=P.parents[2]
def read(p):return json.loads(p.read_text())
native=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')
skin=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json')
anatomy=read(ROOT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
bow=read(ROOT/'SourceAssets/DarkBow20260925/GripV5/grasp_native.json')
profiles=read(P/'grip-surfaces.json')
accepted=read(P.parent/'CameraGripV10/camera-pose.json')
bones=native['bones'];order=sorted(bones,key=lambda n:bones[n]['index'])
by_index={v['index']:n for n,v in bones.items()};parent={n:by_index.get(bones[n]['parent']) for n in order}
def unit(v):return np.asarray(v)/np.linalg.norm(v)
def mat(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y));return np.column_stack((x,y,np.cross(x,y)))
def zx(z):
    z=unit(z);x=unit(np.array([1.,0,0])-z*z[0]);return np.column_stack((x,np.cross(z,x),z))
def swing(a,b):
    a=unit(a);b=unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1.e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()
rest={}
for n in order:
    q=np.array(bones[n]['axes']).T;q=q/np.linalg.norm(q,axis=0)
    rest[n]=mat(R.from_matrix(q).as_matrix(),bones[n]['position'])
local={n:np.linalg.inv(rest[parent[n]])@rest[n] if parent[n] else rest[n] for n in order}
def child(n,ancestor):
    while parent[n]:
        n=parent[n]
        if n==ancestor:return True
    return False
fingers=[n for n in order if child(n,'hand_r')]
arm_names=[n for n in order if n in ('clavicle_r','clavicle_l') or child(n,'clavicle_r') or child(n,'clavicle_l')]

# Anatomical left/right frames have opposite handedness. Conjugating the
# complete deformation maps it to a proper right-handed bone rotation.
frames={s:np.column_stack([unit(anatomy[s][k]) for k in ('across','forward','dorsal')]) for s in ('l','r')}
mirror=frames['r']@np.linalg.inv(frames['l'])
donor={n:np.array(v) for n,v in bow['pose'].items()}
hand_delta=donor['hand_l'][:3,:3]@rest['hand_l'][:3,:3].T
mapped={n:m[:3,:3].copy() for n,m in rest.items()}
for n in ['upperarm_r','lowerarm_r',*fingers]:
    src=n[:-1]+'l'
    if src in donor:
        d=hand_delta.T@donor[src][:3,:3]@rest[src][:3,:3].T
        mapped[n]=R.from_matrix(mirror@d@np.linalg.inv(mirror)@rest[n][:3,:3]).as_matrix()
closed={n:mapped[parent[n]].T@mapped[n] for n in fingers}
digits={d['bone']:d for d in anatomy['r']['digits']}
controls=[(n,'flex') for n in fingers if n in digits]+[('thumb_01_r','opposition'),('thumb_01_r','pronation')]+[(n,'splay') for n in fingers if n in digits and digits[n]['segment']==1 and not n.startswith('thumb')]
axes=[]
for n,kind in controls:
    d=digits[n];axis=unit(np.cross(d['axis'],d['dorsal'])) if kind=='flex' else unit(d['axis']) if kind=='pronation' else unit(d['dorsal']) if kind=='splay' else unit(anatomy['r']['dorsal'])
    hinge=rest[n][:3,:3].T@axis
    if kind=='flex' and d['segment']>=2:
        donor_bend=R.from_matrix(local[n][:3,:3].T@closed[n]).as_rotvec()
        if np.linalg.norm(donor_bend)>.01:hinge=unit(donor_bend)
    axes.append(hinge)

# Fit the actual accepted V7 surface. Each patch has an anatomical identity;
# no whole-finger nearest-point contact objective is used.
weights=skin['weights'];family={'hand_r',*fingers}
ids=np.array([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n in family)>.75])
points=np.array(skin['positions'])[ids];hp=np.column_stack((points,np.ones(len(ids))))
influences={n:np.array([weights[i].get(n,0) for i in ids]) for n in order}
influences={n:w for n,w in influences.items() if np.any(w)}
bind={n:hp@np.linalg.inv(rest[n]).T for n in influences}
patches={}
for n,d in digits.items():
    if d['digit']=='thumb' and d['segment']==1:continue
    candidate=np.array([sum(v for b,v in weights[i].items() if b.startswith(d['digit']) and b.endswith('_r'))>.5 for i in ids])
    center=np.array(d['head'])+np.array(d['axis'])*d['length']*.45-np.array(d['dorsal'])*d['radius']*.78
    if d['digit']=='thumb':
        # The generic V7 dorsal estimate is not a thumb-pad frame. Recover the
        # contact side from the accepted bow thumb and its actual grasp axis.
        src=n[:-1]+'l';dl=next(x for x in anatomy['l']['digits'] if x['bone']==src)
        deform=donor[src][:3,:3]@rest[src][:3,:3].T
        center_l=donor[src][:3,3]+deform@np.array(dl['axis'])*dl['length']*.45
        g=np.array(bow['grip_in_source']);axis=unit(g[:3,2])
        closest=g[:3,3]+axis*np.dot(center_l-g[:3,3],axis)
        pad_side=unit(mirror@deform.T@unit(closest-center_l))
        center=np.array(d['head'])+np.array(d['axis'])*d['length']*.45+pad_side*d['radius']*.78
    candidates=np.flatnonzero(candidate)
    count=6 if d['digit']=='thumb' else 12
    nearest=candidates[np.argsort(np.linalg.norm(points[candidates]-center,axis=1))[:count]]
    patches[n]=nearest
# Two broad palmar support patches behind the MCP row.
wr=rest['hand_r'][:3,3];f=np.array(anatomy['r']['forward']);a=np.array(anatomy['r']['across']);d=np.array(anatomy['r']['dorsal'])
palm_candidates=np.array([sum(v for n,v in weights[i].items() if n=='hand_r' or 'metacarpal_r' in n)>.7 for i in ids])
for name,c in [('palm_radial',wr+f*7+a*1.1-d*.9),('palm_ulnar',wr+f*7-a*1.6-d*.9)]:
    candidates=np.flatnonzero(palm_candidates);patches[name]=candidates[np.argsort(np.linalg.norm(points[candidates]-c,axis=1))[:18]]
hand_q=R.from_quat(accepted['hand_in_staff']['q']).as_matrix()
# Restore the exact camera-facing hand rotation accepted before V12.
# Aligning the donor cylinder axis rotated the wrist/forearm across the view.
# Contact fitting may adapt finger flexion/splay, not turn this whole frame.
initial_p=np.array(accepted['hand_in_staff']['p'])

def hand_pose(x):
    h=mat(hand_q,x[:3]);w={'hand_r':h};q={n:closed[n].copy() for n in fingers}
    for i,(n,kind) in enumerate(controls):q[n]=q[n]@R.from_rotvec(axes[i]*x[3+i]).as_matrix()
    for n in fingers:w[n]=w[parent[n]]@mat(q[n],local[n][:3,3])
    fallback=h@np.linalg.inv(rest['hand_r']);v=np.zeros((len(ids),4))
    for n,weight in influences.items():v+=(bind[n]@w.get(n,fallback@rest[n]).T)*weight[:,None]
    return v[:,:3]+[0,0,32],w,q

def surface_distance(v,radii):
    z=np.clip((v[:,2]-profiles['z'][0])/(profiles['z'][1]-profiles['z'][0]),0,len(radii)-1.000001)
    # Blender -> UE import changes Y sign, preserving the unsymmetric surface.
    az=np.mod(np.arctan2(-v[:,1],v[:,0]),math.tau)*profiles['angle_count']/math.tau
    zi=z.astype(int);ai=az.astype(int);u=z-zi;t=az-ai;j=(ai+1)%profiles['angle_count']
    rr=(radii[zi,ai]*(1-t)+radii[zi,j]*t)*(1-u)+(radii[zi+1,ai]*(1-t)+radii[zi+1,j]*t)*u
    return np.linalg.norm(v[:,:2],axis=1)-rr

variants={}
prior=read(P.parent/'BowBasedGripV12/full-pose.json')
for key,profile in profiles['variants'].items():
    radii=np.array(profile['radii'])
    previous_controls={tuple(c):v for c,v in zip(prior['controls'],prior['variants'][key]['controls_radians'])}
    start=np.r_[initial_p,[previous_controls.get(c,0.) for c in controls]]
    def residual(x):
        v,w,q=hand_pose(x);sd=surface_distance(v,radii)
        terms=[np.minimum(sd-.08,0)*30.]
        for n,patch in patches.items():
            importance=.8 if '_01_' in n else 2.5 if n.startswith('palm') else 1.7
            if n=='thumb_02_r':importance=.3 # MCP supports the opposing tip; not a second shaft clamp.
            if n=='thumb_03_r':importance=6.
            # Contact across a pad region with shallow clearance, not its min.
            terms.append((sd[patch]-.11)*importance)
        terms.extend([(x[:3]-initial_p)*.28,x[3:]*1.4])
        thumb_angle=R.from_matrix(local['thumb_01_r'][:3,:3].T@q['thumb_01_r']).magnitude()
        terms.append(np.array([max(0.,thumb_angle-math.radians(62))*12]))
        # Smooth neighbouring joint changes; preserve donor's continuous arcs.
        for digit in ('index','middle','ring','pinky'):
            k=[i for i,(n,kind) in enumerate(controls) if n.startswith(digit) and kind=='flex']
            terms.append(np.diff(x[3+np.array(k)])*.6)
        return np.concatenate(terms)
    limits=np.r_[np.array([2.,2.,1.5]),np.radians([18 if kind=='splay' else 50 if n.startswith('thumb') or digits[n]['segment']==1 else 40 for n,kind in controls])]
    low=np.r_[initial_p-limits[:3],-limits[3:]];high=np.r_[initial_p+limits[:3],limits[3:]]
    for i,(n,kind) in enumerate(controls):
        if n in ('thumb_02_r','thumb_03_r'):low[3+i]=-math.radians(20)
    fit=least_squares(residual,start,bounds=(low,high),max_nfev=180,ftol=1.e-7,xtol=1.e-7,gtol=1.e-6,diff_step=1.e-4)
    v,w,q=hand_pose(fit.x);sd=surface_distance(v,radii)
    variants[key]={'hand':w['hand_r'].tolist(),'fingers':{n:mat(q[n],local[n][:3,3]).tolist() for n in fingers},
                   'controls_radians':fit.x[3:].tolist(),'fit_cost':float(fit.cost),'fit_completed':bool(fit.success),
                   'pad_mean_clearance_cm':{n:float(np.mean(sd[p])) for n,p in patches.items()},
                   'surface_min_clearance_cm':float(sd.min())}
    print('GRASP_AUTHORED',key,'cost',round(fit.cost,3),'pad gaps', {n:round(float(np.mean(sd[p])),2) for n,p in patches.items()},flush=True)

# Complete support chain. Use the bow donor's wrist-relative forearm/upper-arm
# deformation as a starting point, then recruit the shoulder for native lengths.
ru=rest['lowerarm_r'][:3,3]-rest['upperarm_r'][:3,3]
rl=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3]
def support(hand,seed):
    hd=hand[:3,:3]@rest['hand_r'][:3,:3].T;wrist=hand[:3,3]
    neutral=unit(hd@rl);anchor=np.array(seed[0],dtype=float);pole=np.array(seed[1],dtype=float)
    l1=np.linalg.norm(ru);l2=np.linalg.norm(rl)
    def chain(x):
        shoulder=x[:3];reach=wrist-shoulder;length=np.linalg.norm(reach);axis=reach/length
        along=(l1*l1-l2*l2+length*length)/(2*length)
        down=np.array([0.,0.,-1.]);down=unit(down-axis*np.dot(axis,down));out=np.cross(axis,down)
        elbow=shoulder+axis*along+math.sqrt(max(1.e-8,l1*l1-along*along))*(down*math.cos(x[3])+out*math.sin(x[3]))
        return shoulder,elbow,unit(wrist-elbow)
    def objective(x):
        shoulder,elbow,direction=chain(x)
        angle=math.acos(np.clip(np.dot(direction,neutral),-1,1))
        # A small wrist angle is only one constraint. The shoulder stays at its
        # camera-side anchor and the elbow supports the hand from below/right.
        return np.r_[(shoulder-anchor)*.9,(elbow-pole)*.25,
                     max(0,angle-math.radians(24))*18,
                     max(0,wrist[1]/wrist[0]+.08-elbow[1]/max(elbow[0],1))*3,
                     max(0,elbow[2]+18)*2]
    result=least_squares(objective,np.r_[anchor,.1],bounds=(np.r_[anchor-3.,-1.2],np.r_[anchor+3.,1.2]),max_nfev=100)
    shoulder,elbow,direction=chain(result.x)
    # Donor-relative upper roll, followed by a swing to the supporting elbow.
    upper=hd@mapped['upperarm_r'];upper=swing(upper@rest['upperarm_r'][:3,:3].T@ru,elbow-shoulder)@upper
    lower=frame(direction,hd@a)@frame(rl,a).T@rest['lowerarm_r'][:3,:3]
    return mat(upper,shoulder),mat(lower,elbow)

specs=[('Idle',[44,19,-21],[.22,-.12,.968],[-3,20,-25],[17,14,-42]),
       ('Raised',[39,22,-8],[.52,-.10,.848],[3,22,-20],[19,20,-24]),
       ('Windup',[37,23,-7],[.44,-.12,.890],[3,23,-20],[18,21,-24]),
       ('Release',[55,17,-12],[.940,-.080,.332],[7,21,-23],[30,24,-30]),
       ('Follow',[53,15,-16],[.960,-.100,.262],[6,21,-24],[28,23,-32]),
       ('Run',[40,22,-27],[.22,-.12,.968],[0,21,-26],[15,14,-44])]
poses={}

def parked_left():
    # Fix the shoulder FIRST. V12 placed a rest arm by its hand alone, leaving
    # upperarm_l at (+26,-3,+7) cm directly in front of the camera.
    shoulder=np.array([-5.,-19.,-23.]);wrist=np.array([20.,-19.,-35.]);pole=np.array([4.,-31.,-42.])
    ur=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3];lr=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
    length=np.linalg.norm(wrist-shoulder);axis=unit(wrist-shoulder)
    along=(np.dot(ur,ur)-np.dot(lr,lr)+length*length)/(2*length)
    bend=unit(pole-shoulder-axis*np.dot(pole-shoulder,axis))
    elbow=shoulder+axis*along+bend*math.sqrt(np.dot(ur,ur)-along*along)
    lower_dir=unit(wrist-elbow);upper_dir=unit(elbow-shoulder)
    # Carry the native hand/forearm relation together; no independently guessed
    # wrist quaternion. This is the unloaded arm, not another staff grip.
    across=np.array(anatomy['l']['across']);preferred_across=np.array([0.,0.,1.])
    lower_delta=frame(lower_dir,preferred_across)@frame(lr,across).T
    upper_delta=swing(lower_delta@ur,upper_dir)@lower_delta
    return mat(upper_delta@rest['upperarm_l'][:3,:3],shoulder),mat(lower_delta@rest['lowerarm_l'][:3,:3],elbow),mat(lower_delta@rest['hand_l'][:3,:3],wrist)

for key,v in variants.items():
    clips=[]
    for name,point,axis,shoulder_seed,elbow_seed in specs:
        contact=mat(zx(axis),point);h=contact@np.array(v['hand'])
        upper,lower=support(h,(shoulder_seed,elbow_seed))
        w={n:m.copy() for n,m in rest.items()}
        w['upperarm_r']=upper;w['lowerarm_r']=lower;w['hand_r']=h
        # Clavicle is a translated support anchor; its native local upper-arm
        # translation stays intact. Full helper transforms follow each segment.
        w['clavicle_r'][:3,3]=upper[:3,3]-w['clavicle_r'][:3,:3]@local['upperarm_r'][:3,3]
        for n in order:
            if n in v['fingers']:w[n]=w[parent[n]]@np.array(v['fingers'][n])
            elif child(n,'upperarm_r') and n not in ('lowerarm_r','hand_r'):w[n]=w[parent[n]]@local[n]
        lu,ll,lh=parked_left()
        w['upperarm_l']=lu;w['lowerarm_l']=ll;w['hand_l']=lh
        w['clavicle_l'][:3,3]=lu[:3,3]-w['clavicle_l'][:3,:3]@local['upperarm_l'][:3,3]
        for n in order:
            if child(n,'upperarm_l') and n not in ('lowerarm_l','hand_l'):w[n]=w[parent[n]]@local[n]
        loc={n:np.linalg.inv(w[parent[n]])@w[n] for n in arm_names}
        clips.append({'name':name,'contact':contact.tolist(),'local':{n:m.tolist() for n,m in loc.items()},
                      'component':{n:w[n].tolist() for n in arm_names}})
    poses[key]=clips

data={'revision':13,'units':'native UE cm','source_bow':'DarkBow20260925/GripV5/grasp_native.json',
      'skin':'BarePalmV7/M4','camera_direction':'V10 accepted dorsal facing','variants':variants,'poses':poses,
      'order':arm_names,'parent':parent,'rest':{n:m.tolist() for n,m in rest.items()},
      'skin_pad_vertex_ids':{n:ids[p].tolist() for n,p in patches.items()},'controls':controls,
      'rendered':False,'runtime_tested':False}
(P/'full-pose.json').write_text(json.dumps(data,indent=2),encoding='utf-8')

def numbers(v):return ','.join(f'{x:.10f}' for x in v)
lines=['// Generated by ArmSupportV13/author_pose.py. Native local poses, cm.',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffAuthoredV13 {',
       'inline constexpr int32 PoseCount=6, VariantCount=4;',
       'struct FBone { const TCHAR* Name; FQuat Rotation; FVector Position; };',
       'inline const TCHAR* VariantNames[]={TEXT("false"),TEXT("alloy_grip"),TEXT("pine_grip"),TEXT("sandalwood_grip")};',
       'inline const FTransform HandInGrip[]={']
for v in variants.values():
    h=np.array(v['hand']);lines.append('FTransform(FQuat('+numbers(R.from_matrix(h[:3,:3]).as_quat())+'),FVector('+numbers(h[:3,3])+')),')
lines+=['};',f'inline constexpr int32 BoneCount={len(arm_names)};','inline const FBone Poses[VariantCount][PoseCount][BoneCount]={']
for key,clips in poses.items():
    lines+=['{ // '+key]
    for clip in clips:
        lines+=['{ // '+clip['name']]
        for n,m in clip['local'].items():
            m=np.array(m);lines.append('{TEXT("'+n+'"),FQuat('+numbers(R.from_matrix(m[:3,:3]).as_quat())+'),FVector('+numbers(m[:3,3])+')},')
        lines+=['},']
    lines+=['},']
lines+=['};','}']
(ROOT/'Source/FPSGAME/Weapons/Staff/StaffAuthoredPoseV13.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('STAFF_V13_FULL_POSES_SAVED',len(arm_names),'bones',len(poses)*len(specs),'poses',flush=True)
