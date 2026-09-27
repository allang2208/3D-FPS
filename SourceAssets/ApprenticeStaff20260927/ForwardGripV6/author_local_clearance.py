"""Author local clearance with the accepted V4 wrist rotation locked.
Only finger rotations and translation in the shaft contact plane are adjustable.
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

def residual(x):
    sd=distances(pose(x)[0])
    penetration=np.minimum(sd-.045,0)*6
    contacts=np.array([min(sd[mask])-.075 for mask in groups.values()])*1.4
    regular=np.r_[x[:2]*.3,(x[2:14]-start[2:14])*6,(x[14:17]-start[14:17])*3,(x[17]-1)*3]
    return np.r_[penetration,contacts,regular]

deg=math.pi/180
carry=json.loads((O.parent/'NaturalCarryV5/contact-pose.json').read_text())['authoring_controls']
# Reuse the wider V5 finger opening, but discard all of its wrist rotation.
# The contact plane is fitted as a translation only, leaving the accepted
# V4 palm-facing direction exact in runtime.
start=np.array([0,-4.4]+carry[6:9]*4+carry[9:12]+[1.])
lower=[-1,-4.8]+list(start[2:14]-.10)+list(start[14:17]-6*deg)+[.8]
upper=[1,0]+list(start[2:14]+.10)+list(start[14:17]+6*deg)+[1.2]
result=least_squares(residual,start,bounds=(lower,upper),max_nfev=100,diff_step=1.e-4)
points,h,rotations=pose(result.x)
data={'revision':6,'method':'V4 wrist rotation locked; bounded local contact adjustments',
      'authoring_controls':result.x.tolist(),'tested':False,'rendered':False,
      'hand_rotation_delta_degrees':0,'palm_offset_cm':result.x[:2].tolist(),
      'local_corrections':{n:Rot.from_matrix(closed[n].T@q).as_quat().tolist() for n,q in rotations.items()},
      'solve_objective':{'minimum_skin_distance_cm':float(distances(points).min()),
                         'regions_cm':{n:float(distances(points)[mask].min()) for n,mask in groups.items()}}}
(O/'local-clearance.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
def vals(v):return ','.join(f'{x:.10f}' for x in v)
lines=['// V6: local contact corrections relative to the accepted V4 grasp.',
       '// Wrist orientation comes only from StaffGripPose.cpp; never fitted here.',
       '// SourceAssets/ApprenticeStaff20260927/ForwardGripV6/author_local_clearance.py',
       '#pragma once','#include "CoreMinimal.h"','namespace StaffGripContact {',
       'inline const FVector OffsetInGrip('+vals(data['palm_offset_cm']+[0.])+');',
       'struct FEntry { const TCHAR* Bone; FQuat LocalOffset; };','inline const FEntry Fingers[]={']
lines+=['    {TEXT("'+n+'"),FQuat('+vals(q)+')},' for n,q in data['local_corrections'].items()
        if np.linalg.norm(q[:3])>1.e-6]
lines+=['};','}']
(PROJECT/'Source/FPSGAME/Weapons/Staff/StaffGripContact.h').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('LOCAL_CLEARANCE_AUTHORED',data['authoring_controls'],data['solve_objective'])
