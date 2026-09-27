"""Refine only wrist support and thumb details around the user-accepted V10 direction.
The hand contact transform and all four finger local rotations stay frozen.
This produces source pose data, not a render or a runtime acceptance report.
"""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from scipy.optimize import least_squares

O=Path(__file__).resolve().parent;PROJECT=O.parents[2]
native=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())
skin=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json').read_text())
donor=json.loads((O.parent/'ClosedGripV4/grasp-source.json').read_text())['fingers']
profile=json.loads((O.parent/'NaturalCarryV5/handle-profile.json').read_text());radii=np.array(profile['radii'])
bones=native['bones'];names=sorted(bones,key=lambda n:bones[n]['index']);by_index={b['index']:n for n,b in bones.items()}
parents={n:by_index.get(b['parent']) for n,b in bones.items()}
def unit(x):return x/np.linalg.norm(x)
def matrix(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
rest={n:matrix(Rot.from_matrix(np.array(b['axes']).T/100).as_matrix(),b['position']) for n,b in bones.items()}
local={n:np.linalg.inv(rest[parents[n]])@rest[n] if parents[n] else rest[n] for n in names}
hand='hand_r';forward=unit(rest['middle_01_r'][:3,3]-rest[hand][:3,3])
across=rest['index_01_r'][:3,3]-rest['pinky_01_r'][:3,3];across=unit(across-forward*np.dot(across,forward))
normal=np.cross(across,forward);frame=np.column_stack((across,forward,normal))
desired={n:m[:3,:3].copy() for n,m in rest.items()}
for n,q in donor.items():desired[n]=frame@Rot.from_quat(q).as_matrix()@frame.T@rest[n][:3,:3]
closed={n:desired[parents[n]].T@desired[n] for n in donor}
children=[n for n in names if n in donor]
base_pose={n:m.copy() for n,m in rest.items()}
for n in children:base_pose[n]=base_pose[parents[n]]@matrix(closed[n],local[n][:3,3])

# The final V7 skin, not bone-end probes, defines contact. Only hand skin is fitted.
family={hand,*children};weights=skin['weights'];ids=[i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n in family)>.8]
points=np.array(skin['positions'])[ids];homogeneous=np.column_stack((points,np.ones(len(points))))
influences={n:np.array([weights[i].get(n,0) for i in ids]) for n in names}
influences={n:w for n,w in influences.items() if np.any(w)}
mapped={n:homogeneous@np.linalg.inv(rest[n]).T for n in influences}
groups={d:np.array([sum(v for n,v in weights[i].items() if n.startswith(d) and n.endswith('_r'))>.35 for i in ids]) for d in ('index','middle','ring','pinky','thumb')}
palm_forward=(points-rest[hand][:3,3])@forward
groups['palm']=np.array([sum(v for n,v in weights[i].items() if n==hand or ('metacarpal_r' in n))>.55 for i in ids]) & (palm_forward>3) & (palm_forward<8.5)
delta={n:Rot.from_matrix(local[n][:3,:3].T@closed[n]).as_rotvec() for n in children}
thumb_axes={}
for n,nxt in [('thumb_01_r','thumb_02_r'),('thumb_02_r','thumb_03_r')]:
    direction=unit(rest[nxt][:3,3]-rest[n][:3,3]);hinge=unit(np.cross(direction,normal))
    thumb_axes[n]=(rest[parents[n]][:3,:3].T@hinge,rest[parents[n]][:3,:3].T@normal)

def distances(points):
    z=np.clip((points[:,2]-22)*2,0,len(radii)-1.000001);a=np.mod(np.arctan2(points[:,1],points[:,0]),math.tau)*96/math.tau
    zi=z.astype(int);ai=a.astype(int);za=z-zi;aa=a-ai
    radius=((1-aa)*radii[zi,ai]+aa*radii[zi,(ai+1)%96])*(1-za)+((1-aa)*radii[zi+1,ai]+aa*radii[zi+1,(ai+1)%96])*za
    return np.linalg.norm(points[:,:2],axis=1)-radius


def frame_zx(z,x):
    z=unit(z);x=unit(x-z*np.dot(z,x))
    return np.column_stack((x,np.cross(z,x),z))

def frame_xz(x,z):
    x=unit(x);z=unit(z-x*np.dot(x,z))
    return np.column_stack((x,np.cross(z,x),z))

def frame_xy(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y))
    return np.column_stack((x,y,np.cross(x,y)))

accepted=json.loads((O/'accepted-direction.json').read_text())
hand_in_staff=matrix(Rot.from_quat(accepted['hand_in_staff']['q']).as_matrix(),accepted['hand_in_staff']['p'])
frozen={n:closed[n]@Rot.from_quat(accepted['local_corrections'][n]).as_matrix() for n in children}
staff_rotation=frame_zx(np.array([.22,-.12,.968]),np.array([1.,0,0]))
contact_point=np.array([44.,19.,-21.])
thumb_mask=groups['thumb']
tip_mask=np.array([weights[i].get('thumb_03_r',0)>.55 for i in ids])

def thumb_pose(x):
    q={n:m.copy() for n,m in frozen.items()}
    n='thumb_01_r'
    q[n]=Rot.from_rotvec(thumb_axes[n][0]*x[0]).as_matrix()@Rot.from_rotvec(thumb_axes[n][1]*x[1]).as_matrix()@local[n][:3,:3]
    # MCP/IP bend only in the native flexion plane. The old thumb_02 correction
    # introduced a second lateral swing after a 57-degree CMC displacement.
    for n,k in [('thumb_02_r',2),('thumb_03_r',3)]:
        q[n]=local[n][:3,:3]@Rot.from_rotvec(delta[n]*x[k]).as_matrix()
    p={hand:hand_in_staff}
    for n in children:p[n]=p[parents[n]]@matrix(q[n],local[n][:3,3])
    fallback=hand_in_staff@np.linalg.inv(rest[hand]);skinned=np.zeros((len(ids),4))
    for n,w in influences.items():skinned+=(mapped[n]@p.get(n,fallback@rest[n]).T)*w[:,None]
    return skinned[:,:3]+np.array([0,0,32]),q,p

thumb_start=np.array([-.35,-.4,.58,.45])
def thumb_residual(x):
    surface,q,p=thumb_pose(x);sd=distances(surface)
    root_angle=Rot.from_matrix(local['thumb_01_r'][:3,:3].T@q['thumb_01_r']).magnitude()
    a=contact_point+staff_rotation@p['thumb_01_r'][:3,3]
    tip=p['thumb_03_r'][:3,3]-p['thumb_03_r'][:3,0]*1.8
    b=contact_point+staff_rotation@tip
    screen=unit(b[1:]/b[0]-a[1:]/a[0])
    return np.r_[np.minimum(sd[thumb_mask]-.04,0)*6,
                 (min(sd[tip_mask])-.12)*2,
                 max(0,root_angle-math.radians(34))*30,
                 (x-thumb_start)*np.array([5.,5.,6.,6.]),
                 (screen-unit(np.array([-1.,.18])))*1.5]

fit=least_squares(thumb_residual,thumb_start,bounds=([-.62,-.62,.25,.15],[.15,.15,1.05,.8]),max_nfev=120,diff_step=1.e-4)
surface,rotations,chain=thumb_pose(fit.x)

# Freeze the accepted wrist/contact. Move the supporting arm, not the fist.
wrist=np.array(accepted['idle_camera']['wrist'])
wrist_rotation=Rot.from_quat(accepted['idle_camera']['hand_q']).as_matrix()
hand_deform=wrist_rotation@rest[hand][:3,:3].T
ru=rest['lowerarm_r'][:3,3]-rest['upperarm_r'][:3,3]
rl=rest[hand][:3,3]-rest['lowerarm_r'][:3,3]
upper_length=np.linalg.norm(ru);lower_length=np.linalg.norm(rl)
neutral_forearm=unit(hand_deform@rl)

def support(x):
    shoulder=x[:3];reach=wrist-shoulder;length=np.linalg.norm(reach);axis=reach/length
    along=(upper_length**2-lower_length**2+length**2)/(2*length)
    radius=math.sqrt(max(1.e-8,upper_length**2-along**2))
    low=np.array([0.,0.,-1.]);low=unit(low-axis*np.dot(axis,low));side=np.cross(axis,low)
    elbow=shoulder+axis*along+radius*(low*math.cos(x[3])+side*math.sin(x[3]))
    return shoulder,elbow,unit(wrist-elbow)

def support_residual(x):
    shoulder,elbow,direction=support(x)
    bend=math.acos(np.clip(np.dot(direction,neutral_forearm),-1,1))
    # Wrist continuity takes priority over placing the elbow far screen-right.
    # The previous screen-right objective forced a visible 20-degree kink.
    return np.r_[max(0,bend-math.radians(5))*65,
                 (shoulder-np.array([1.,20.,-23.]))*.22,
                 (elbow-np.array([19.,11.,-41.]))*.07]

arm_fit=least_squares(support_residual,np.array([1.,20.,-23.,.5]),
                     bounds=([-5,10,-30,-1.6],[10,25,-15,1.6]),max_nfev=120)
shoulder,elbow,forearm_dir=support(arm_fit.x)
upper_dir=unit(elbow-shoulder);plane=unit(np.cross(upper_dir,forearm_dir));ref_plane=unit(np.cross(ru,rl))
upper_rotation=frame_xz(upper_dir,plane)@frame_xz(ru,ref_plane).T@rest['upperarm_r'][:3,:3]
ref_across=unit(rest['index_01_r'][:3,3]-rest['pinky_01_r'][:3,3]);posed_across=hand_deform@ref_across
lower_rotation=frame_xy(forearm_dir,posed_across)@frame_xy(rl,ref_across).T@rest['lowerarm_r'][:3,:3]
upper_across=upper_rotation@rest['upperarm_r'][:3,:3].T@ref_across
u=unit(upper_across-upper_dir*np.dot(upper_across,upper_dir));p=unit(posed_across-upper_dir*np.dot(posed_across,upper_dir))
roll=np.clip(math.atan2(np.dot(upper_dir,np.cross(u,p)),np.dot(u,p))*.18,-math.radians(12),math.radians(12))
upper_rotation=Rot.from_rotvec(upper_dir*roll).as_matrix()@upper_rotation

corrections=dict(accepted['local_corrections'])
for n in ('thumb_01_r','thumb_02_r','thumb_03_r'):
    corrections[n]=Rot.from_matrix(closed[n].T@rotations[n]).as_quat().tolist()
data={'revision':11,'method':'frozen V10 hand/contact and four fingers; native thumb flexion; wrist-led arm support',
      'tested':False,'rendered':False,'hand_in_staff':accepted['hand_in_staff'],'local_corrections':corrections,
      'thumb_controls':fit.x.tolist(),
      'idle_camera':{'shoulder':shoulder.tolist(),'elbow':elbow.tolist(),'wrist':wrist.tolist(),
                     'upper_q':Rot.from_matrix(upper_rotation).as_quat().tolist(),
                     'lower_q':Rot.from_matrix(lower_rotation).as_quat().tolist(),'hand_q':accepted['idle_camera']['hand_q']},
      'authoring_objective':{'wrist_axis_bend_degrees':float(np.degrees(np.arccos(np.clip(np.dot(forearm_dir,neutral_forearm),-1,1)))),
                             'thumb_root_from_native_degrees':float(np.degrees(Rot.from_matrix(local['thumb_01_r'][:3,:3].T@rotations['thumb_01_r']).magnitude())),
                             'minimum_thumb_skin_distance_cm':float(distances(surface)[thumb_mask].min())}}
(O/'wrist-detail.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
def vals(v):return ','.join(f'{float(x):.10f}' for x in v)
lines=['// V11: accepted V10 contact/direction; relaxed native thumb joints.',
       '// SourceAssets/ApprenticeStaff20260927/WristDetailV11/author_wrist_detail.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffPhotoGripV11 {',
       'inline const FVector HandPosition('+vals(data['hand_in_staff']['p'])+');',
       'inline const FQuat HandRotation('+vals(data['hand_in_staff']['q'])+');',
       'struct FEntry { const TCHAR* Bone; FQuat LocalOffset; };','inline const FEntry Fingers[]={']
lines+=['    {TEXT("'+n+'"),FQuat('+vals(q)+')},' for n,q in corrections.items() if np.linalg.norm(q[:3])>1.e-6]
lines+=['};','}']
(PROJECT/'Source/FPSGAME/Weapons/Staff/StaffGripContact.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
lines=['// V11: wrist-led support; V10 hand stays fixed in camera coordinates (cm).',
       '// SourceAssets/ApprenticeStaff20260927/WristDetailV11/author_wrist_detail.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffIdlePoseV11 {']
for name,value in [('Shoulder',shoulder),('Elbow',elbow),('Wrist',wrist)]:lines+=['inline const FVector '+name+'('+vals(value)+');']
for name,value in [('UpperRotation',upper_rotation),('LowerRotation',lower_rotation),('HandRotation',wrist_rotation)]:
    lines+=['inline const FQuat '+name+'('+vals(Rot.from_matrix(value).as_quat())+');']
lines+=['}']
(PROJECT/'Source/FPSGAME/Weapons/Staff/StaffIdlePose.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('STAFF_WRIST_V11_AUTHORED',json.dumps({'arm':data['idle_camera'],'thumb_controls':data['thumb_controls'],'objective':data['authoring_objective']}))
