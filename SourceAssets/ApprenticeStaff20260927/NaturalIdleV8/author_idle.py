"""Author a complete staff idle from the accepted V4 palm direction and V7 skin.
The whole forehand contact is frozen while authoring natural shoulder/elbow support.
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
centers=[]
for digit in ('index','middle','ring','pinky'):
    a,b,c=[base_pose[f'{digit}_{i:02d}_r'][:3,3] for i in (1,2,3)]
    u=b-a;v=c-a;w=np.cross(u,v)
    centers.append(a+(np.dot(u,u)*np.cross(v,w)+np.dot(v,v)*np.cross(w,u))/(2*np.dot(w,w)))
center=np.mean(centers,axis=0);axis=unit(centers[0]-centers[3]);side=rest[hand][:3,3]-center
side=unit(side-axis*np.dot(side,axis));grip=matrix(np.column_stack((side,np.cross(axis,side),axis)),center)
base_hand=np.linalg.inv(grip)@rest[hand]
around=Rot.from_euler('z',math.atan2(.835,-.55)).as_matrix()

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

def pose(x):
    # V4 wrist orientation and grip height are immutable. Only contact-plane
    # translation is available; the optimizer cannot turn the palm around.
    h=base_hand.copy();h[:2,3]+=x[:2]
    p={hand:h};q={}
    for n in children:
        part=n.split('_')[1]
        digit=n.split('_')[0]
        opening=x[2+('index','middle','ring','pinky').index(digit)*3+int(part)-1] if part.isdigit() and digit!='thumb' else 1
        q[n]=local[n][:3,:3]@Rot.from_rotvec(delta[n]*opening).as_matrix()
        if n=='thumb_01_r':
            q[n]=Rot.from_rotvec(thumb_axes[n][0]*x[14]).as_matrix()@Rot.from_rotvec(thumb_axes[n][1]*x[15]).as_matrix()@q[n]
        elif n=='thumb_02_r':
            q[n]=Rot.from_rotvec(thumb_axes[n][0]*x[16]).as_matrix()@q[n]
        elif n=='thumb_03_r':
            q[n]=local[n][:3,:3]@Rot.from_rotvec(delta[n]*x[17]).as_matrix()
        p[n]=p[parents[n]]@matrix(q[n],local[n][:3,3])
    fallback=h@np.linalg.inv(rest[hand]);skinned=np.zeros((len(ids),4))
    for n,w in influences.items():skinned+=(mapped[n]@p.get(n,fallback@rest[n]).T)*w[:,None]
    return skinned[:,:3]@around.T+np.array([0,0,32]),h,q

def distances(points):
    z=np.clip((points[:,2]-22)*2,0,len(radii)-1.000001);a=np.mod(np.arctan2(points[:,1],points[:,0]),math.tau)*96/math.tau
    zi=z.astype(int);ai=a.astype(int);za=z-zi;aa=a-ai
    radius=((1-aa)*radii[zi,ai]+aa*radii[zi,(ai+1)%96])*(1-za)+((1-aa)*radii[zi+1,ai]+aa*radii[zi+1,(ai+1)%96])*za
    return np.linalg.norm(points[:,:2],axis=1)-radius


# Freeze the current forehand contact as one unit. The native M4 rest already
# bends the joints, so donor opening is not an anatomical joint angle. Idle
# arm support must not re-fit the palm or flatten/re-curl the fingers.
controls=np.array(json.loads((O.parent/'ForwardGripV6/local-clearance.json').read_text())['authoring_controls'])
surface,hand_in_grip,rotations=pose(controls)

# Author the complete idle support in camera space. The staff's placement and
# the accepted forehand direction stay unchanged. Solve the elbow along the
# reachable circle while favoring a neutral wrist and a relaxed, low elbow.
def frame_zx(z,x):
    z=unit(z);x=unit(x-z*np.dot(z,x))
    return np.column_stack((x,np.cross(z,x),z))

def frame_xz(x,z):
    x=unit(x);z=unit(z-x*np.dot(x,z))
    return np.column_stack((x,np.cross(z,x),z))

staff_rotation=frame_zx(np.array([.22,-.12,.968]),np.array([1.,0,0]))
contact_rotation=staff_rotation@around
contact_point=np.array([44.,19.,-21.])
wrist=contact_point+contact_rotation@hand_in_grip[:3,3]
wrist_rotation=contact_rotation@hand_in_grip[:3,:3]
ru=rest['lowerarm_r'][:3,3]-rest['upperarm_r'][:3,3]
rl=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3]
upper_length=np.linalg.norm(ru);lower_length=np.linalg.norm(rl)
hand_deform=wrist_rotation@rest['hand_r'][:3,:3].T
neutral_forearm=unit(hand_deform@rl)

def support(x):
    shoulder=x[:3]
    reach=wrist-shoulder;length=np.linalg.norm(reach);axis=reach/length
    along=(upper_length**2-lower_length**2+length**2)/(2*length)
    radius=math.sqrt(max(1.e-8,upper_length**2-along**2))
    low=np.array([0.,0.,-1.]);low=unit(low-axis*np.dot(axis,low))
    side=np.cross(axis,low)
    elbow=shoulder+axis*along+radius*(low*math.cos(x[3])+side*math.sin(x[3]))
    return shoulder,elbow,unit(wrist-elbow)

def support_residual(x):
    shoulder,elbow,direction=support(x)
    bend=math.acos(np.clip(np.dot(direction,neutral_forearm),-1,1))
    # A perfectly straight wrist would force the elbow up/out beside the hand.
    # Author a relaxed elbow with a bounded, slightly bent wrist instead.
    return np.r_[max(0,bend-math.radians(24))*25,
                 (shoulder-np.array([1.,20.,-24.]))*.50,
                 (elbow-np.array([18.,30.,-38.]))*.22]

arm_result=least_squares(support_residual,np.array([1.,20.,-24.,.15]),
                         bounds=([-3,17,-28,-1.35],[6,24,-21,1.35]),max_nfev=100)
shoulder,elbow,forearm_dir=support(arm_result.x)
upper_dir=unit(elbow-shoulder)
plane=unit(np.cross(upper_dir,forearm_dir))
ref_plane=unit(np.cross(ru,rl))
upper_rotation=frame_xz(upper_dir,plane)@frame_xz(ru,ref_plane).T@rest['upperarm_r'][:3,:3]
ref_across=unit(rest['index_01_r'][:3,3]-rest['pinky_01_r'][:3,3])
posed_across=hand_deform@ref_across

def frame_xy(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y))
    return np.column_stack((x,y,np.cross(x,y)))

lower_rotation=frame_xy(forearm_dir,posed_across)@frame_xy(rl,ref_across).T@rest['lowerarm_r'][:3,:3]
upper_across=upper_rotation@rest['upperarm_r'][:3,:3].T@ref_across
u=unit(upper_across-upper_dir*np.dot(upper_across,upper_dir))
p=unit(posed_across-upper_dir*np.dot(posed_across,upper_dir))
support_roll=np.clip(math.atan2(np.dot(upper_dir,np.cross(u,p)),np.dot(u,p))*.18,-math.radians(12),math.radians(12))
upper_rotation=Rot.from_rotvec(upper_dir*support_roll).as_matrix()@upper_rotation

data={'revision':8,'source':'ClosedGripV4/grasp-source.json; V7 native M4 skin',
      'method':'frozen V6 forehand contact; authored shoulder-elbow-wrist support and upper-arm roll',
      'tested':False,'rendered':False,'authoring_controls':controls.tolist(),
      'hand_in_grip':{'p':hand_in_grip[:3,3].tolist(),'q':Rot.from_matrix(hand_in_grip[:3,:3]).as_quat().tolist()},
      'palm_offset_cm':controls[:2].tolist(),
      'local_corrections':{n:Rot.from_matrix(closed[n].T@q).as_quat().tolist() for n,q in rotations.items()},
      'idle_camera':{'shoulder':shoulder.tolist(),'elbow':elbow.tolist(),'wrist':wrist.tolist(),
                     'upper_q':Rot.from_matrix(upper_rotation).as_quat().tolist(),
                     'lower_q':Rot.from_matrix(lower_rotation).as_quat().tolist(),
                     'hand_q':Rot.from_matrix(wrist_rotation).as_quat().tolist(),
                     'contact_q':Rot.from_matrix(contact_rotation).as_quat().tolist()},
      'authoring_objective':{'wrist_axis_bend_degrees':float(np.degrees(np.arccos(np.clip(np.dot(forearm_dir,neutral_forearm),-1,1))))}}
(O/'idle-pose.json').write_text(json.dumps(data,indent=2),encoding='utf-8')

def vals(v):return ','.join(f'{float(x):.10f}' for x in v)

lines=['// V8: preserve the V6 forehand contact; idle support is in StaffIdlePose.h.',
       '// SourceAssets/ApprenticeStaff20260927/NaturalIdleV8/author_idle.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffGripContact {',
       'inline const FVector OffsetInGrip('+vals(data['palm_offset_cm']+[0.])+');',
       'struct FEntry { const TCHAR* Bone; FQuat LocalOffset; };','inline const FEntry Fingers[]={']
lines+=['    {TEXT("'+n+'"),FQuat('+vals(q)+')},' for n,q in data['local_corrections'].items() if np.linalg.norm(q[:3])>1.e-6]
lines+=['};','}']
(PROJECT/'Source/FPSGAME/Weapons/Staff/StaffGripContact.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')

lines=['// V8 native V7/M4 full-arm idle in camera coordinates; dimensions are cm.',
       '// SourceAssets/ApprenticeStaff20260927/NaturalIdleV8/author_idle.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffIdlePose {']
for name,value in [('Shoulder',shoulder),('Elbow',elbow),('Wrist',wrist)]:
    lines+=['inline const FVector '+name+'('+vals(value)+');']
for name,value in [('UpperRotation',upper_rotation),('LowerRotation',lower_rotation),('HandRotation',wrist_rotation),('ContactRotation',contact_rotation)]:
    lines+=['inline const FQuat '+name+'('+vals(Rot.from_matrix(value).as_quat())+');']
lines+=['}']
(PROJECT/'Source/FPSGAME/Weapons/Staff/StaffIdlePose.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('STAFF_IDLE_V8_AUTHORED',json.dumps({'offset_cm':data['palm_offset_cm'],'controls':data['authoring_controls'],
      'arm':data['idle_camera'],'objective':data['authoring_objective']}))
