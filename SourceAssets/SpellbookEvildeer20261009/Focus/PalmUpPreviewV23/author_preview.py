"""Rigid held-turn preview: forearm -> unchanged wrist/fingers -> fixed book.

Only the requested holding turn is shown. Reduced forearm rotation and
arm reach place the attached book at the original reading spine location.
The original idle wrist, fingers and book attachment stay fixed.
Runtime sources and the active authoring entry are untouched.
"""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares

OUT=Path(__file__).resolve().parent;P=OUT.parent;ROOT=P.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v):return np.asarray(v)/np.linalg.norm(v)
def mat(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def ease(t):
    u=np.clip(t,0,1);return u*u*u*(u*(6*u-15)+10)
def swing(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()

grip=read(P.parent/'GripPhotoV3/grip.json')
landing=read(P/'VideoRecovery20261010/landing-baseline-v9.json')
native=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')['bones']
names=grip['arm_order'];byindex={b['index']:n for n,b in native.items()}
parent={n:byindex.get(b['parent']) for n,b in native.items()}
rest={}
for n,b in native.items():
    q=np.array(b['axes']).T;q/=np.linalg.norm(q,axis=0)
    rest[n]=mat(R.from_matrix(q).as_matrix(),b['position'])
local={n:np.linalg.inv(rest[parent[n]])@m if parent[n] else m for n,m in rest.items()}
base={n:np.array(m) for n,m in grip['poses'][0]['component'].items()}
fixed={n:np.array(m) for n,m in grip['poses'][0]['local'].items()}
end_index=min(range(len(landing['times'])),key=lambda i:abs(landing['times'][i]*landing['seconds']['total']-.76))
support={n:np.array(m) for n,m in landing['poses'][end_index]['component'].items()}
mount=np.array(grip['book_in_hand']);lower=np.array([0.,0.,-5.])
turn_end=.90;duration=1.45
s0,e0,w0=[base[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
s1,e1,w1=[support[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
lu,ll=np.linalg.norm(e0-s0),np.linalg.norm(w0-e0)
hand_local=np.linalg.inv(base['lowerarm_l'])@base['hand_l']
# Stop before the previous 233 degree overshoot. The wrist and every
# finger retain the exact carry transform throughout this half turn.
roll=math.radians(180.)
upper_transport=swing(e0-s0,e1-s1)@base['upperarm_l'][:3,:3]
upper_roll=float(np.dot(R.from_matrix(support['upperarm_l'][:3,:3]@upper_transport.T).as_rotvec(),unit(e1-s1)))

def pose(age):
    u=ease(age/turn_end);shoulder=(1-u)*s0+u*s1;wrist=(1-u)*w0+u*w1
    axis=unit(wrist-shoulder);reach=np.linalg.norm(wrist-shoulder)
    along=(lu*lu-ll*ll+reach*reach)/(2*reach);circle=shoulder+axis*along
    pole=(1-u)*e0+u*e1;radial=unit(pole-circle-axis*np.dot(pole-circle,axis))
    elbow=circle+radial*math.sqrt(max(0,lu*lu-along*along))
    upper_axis=unit(elbow-shoulder);forearm_axis=unit(wrist-elbow)
    upper=R.from_rotvec(upper_axis*upper_roll*u).as_matrix()@swing(e0-s0,upper_axis)@base['upperarm_l'][:3,:3]
    forearm=R.from_rotvec(forearm_axis*roll*u).as_matrix()@swing(w0-e0,forearm_axis)@base['lowerarm_l'][:3,:3]
    world={n:m.copy() for n,m in rest.items()}
    world['clavicle_l']=base['clavicle_l'].copy()
    world['clavicle_l'][:3,3]=shoulder-world['clavicle_l'][:3,:3]@local['upperarm_l'][:3,3]
    world['upperarm_l']=mat(upper,shoulder);world['lowerarm_l']=mat(forearm,elbow)
    world['hand_l']=world['lowerarm_l']@hand_local
    for n in names:
        if n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'):continue
        world[n]=world[parent[n]]@(local[n] if 'twist_' in n else fixed[n])
    if age<=0:return grip['poses'][0]
    return {'local':{n:(np.linalg.inv(world[parent[n]])@world[n]).tolist() for n in names},
            'component':{n:world[n].tolist() for n in names}}

# Solve the arm's reach to the approved reading spine position. The book
# has no independent transform: its endpoint is always hand @ fixed mount.
# Keep the shoulder near its original location rather than lifting the whole
# arm mesh into the camera; the elbow bends with constant segment lengths.
reading=np.array(landing['reading_book_camera'])
initial_wrist=w1.copy()
def placement_error(wrist_position):
    global w1
    w1=np.asarray(wrist_position)
    end_hand=np.array(pose(turn_end)['component']['hand_l'])
    return (end_hand@mount)[:3,3]+lower-reading[:3,3]
solution=least_squares(placement_error,initial_wrist+np.array([4.,-3.,14.]),max_nfev=60)
w1=solution.x.copy()

times=[i/60 for i in range(math.ceil(duration*60)+1)];poses=[pose(t) for t in times]
book_frames=[]
for sample in poses:
    book=np.array(sample['component']['hand_l'])@mount
    book[:3,3]+=lower
    book_frames.append(book.tolist())
data={'revision':'V23 reduced rigid turn to approved reading position','fps':60,'times':times,'arm_order':names,
      'poses':poses,'book_frames':book_frames,'book_in_hand':mount.tolist(),'wrist_in_forearm':hand_local.tolist(),
      'events':{'turn_end':turn_end,'duration':duration,'open_start':99.,'open_end':100.},
      'lowerarm_roll_degrees':math.degrees(roll),'end_wrist_cm':w1.tolist(),
      'target_reading_book_camera':reading.tolist(),'show_only_held_turn':True,
      'runtime_integrated':False,'reading_endpoint_changed':False,
      'contract':'fixed idle wrist and every finger; book = hand @ original BookInHand on every frame'}
(OUT/'candidate.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print(json.dumps({'output':str(OUT/'candidate.json'),'keys':len(times),'forearm_roll_degrees':math.degrees(roll),'book_motion':'fixed BookInHand only'}))
