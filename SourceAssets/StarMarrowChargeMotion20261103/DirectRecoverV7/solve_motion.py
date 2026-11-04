"""Preserve accepted V6 through release; replace its long recovery with one 0.4 s return."""
from pathlib import Path
import sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'AuditV3'))
from motion_math import *
from scipy.interpolate import CubicHermiteSpline
P=Path(__file__).resolve().parent
variant='LongGrip' if '--long-grip' in sys.argv else 'Standard'
FPS=120;START=1.8;END=2.2;SPAN=END-START
baseline=json.loads((P.parent/'FirstMotionV6'/variant/'poses.json').read_text())
all_poses=[{n:np.array(m) for n,m in zip(baseline['names'],row)} for row in baseline['poses']]
idle=all_poses[-1];cut=round(START*FPS);start=all_poses[cut];before=all_poses[cut-1]

def scale(m):return np.linalg.norm(m[:3,:3],axis=0)
def local(pose,n):return np.linalg.inv(pose[parents[n]])@pose[n] if parents[n] else pose[n]
def ease(t):
    t=np.clip(t,0.,1.);return t*t*t*(10.+t*(-15.+6.*t))
def between(a,b):
    a,b=unit(a),unit(b);return R.from_quat(unit(np.r_[np.cross(a,b),1.+a@b])).as_matrix()
def blend(a,b,t):return a@R.from_rotvec(R.from_matrix(a.T@b).as_rotvec()*t).as_matrix()

# Local joint rotation curves retain bone lengths and the incoming velocity.
# No world-space matrix interpolation or second delayed return after idle.
curves={}
for n in names:
    a,b,z=local(start,n),local(before,n),local(idle,n)
    q=rotation(a);target=R.from_matrix(q.T@rotation(z)).as_rotvec()
    velocity=-R.from_matrix(q.T@rotation(b)).as_rotvec()*FPS
    curves[n]=(a,z,CubicHermiteSpline([0.,SPAN],[np.zeros(3),target],[velocity,np.zeros(3)]))

# The left hand comes from the clear withdrawal pose straight to its grip.
# It closes while still outside the pommel instead of parking and circling it.
lh='hand_l';lu='upperarm_l';ll='lowerarm_l'
hand_curve=CubicHermiteSpline([0.,SPAN],[start[lh][:3,3],idle[lh][:3,3]],
    [(start[lh][:3,3]-before[lh][:3,3])*FPS,np.zeros(3)])
hand_q0=rotation(start[lh]);hand_rot=CubicHermiteSpline([0.,SPAN],
    [np.zeros(3),R.from_matrix(hand_q0.T@rotation(idle[lh])).as_rotvec()],
    [-R.from_matrix(hand_q0.T@rotation(before[lh])).as_rotvec()*FPS,np.zeros(3)])
a0,e0,h0=[idle[n][:3,3] for n in [lu,ll,lh]]
u0=e0-a0;f0=h0-e0;normal=unit(np.cross(u0,f0));upper=np.linalg.norm(u0);fore=np.linalg.norm(f0)
Bu=frame(u0,normal);Bl=frame(f0,normal);ru=rotation(idle[lu]);rl=rotation(idle[ll])
rel=rl.T@rotation(idle[lh]);axis=rl.T@unit(f0);reach0=unit(h0-a0);pole0=unit(u0-reach0*(u0@reach0))
wrist_axis=rotation(rest[lh]).T@unit(rest[lh][:3,3]-rest[ll][:3,3])
neutral=between(rel@wrist_axis,axis)@rel
reach_start=unit(start[lh][:3,3]-start[lu][:3,3])
pole_start=unit(start[ll][:3,3]-start[lu][:3,3]-reach_start*((start[ll][:3,3]-start[lu][:3,3])@reach_start))
base_pole=between(reach0,reach_start)@pole0
phi_start=np.arctan2(reach_start@np.cross(base_pole,pole_start),base_pole@pole_start)

# Preserve the right hand's grip during the direct return. Only the recovery
# sword track is derived from the hand; the accepted prefix is copied verbatim.
grip0=np.linalg.inv(start['WPN_root'])@start['hand_r']
grip1=np.linalg.inv(idle['WPN_root'])@idle['hand_r']
rows=all_poses[:cut+1]
for frame_index in range(cut+1,round(END*FPS)+1):
    dt=frame_index/FPS-START;x=dt/SPAN;w=ease(x);pose={}
    for n in names:
        a,z,curve=curves[n];q=rotation(a)@R.from_rotvec(curve(dt)).as_matrix()
        position=a[:3,3]*(1.-w)+z[:3,3]*w
        # The support fingers close before the palm arrives at the handle.
        if n.endswith('_l') and n.split('_')[0] in ['thumb','index','middle','ring','pinky']:
            q=blend(rotation(a),rotation(z),ease(x/.60))
        m=make(position,q,scale(a)*(1.-w)+scale(z)*w)
        pose[n]=pose.get(parents[n],np.eye(4))@m
    h=hand_curve(dt)
    h+=np.array([-.025,-.012,.012])*(16.*x*x*(1.-x)*(1.-x))
    a=pose[lu][:3,3];reach=np.linalg.norm(h-a);direction=unit(h-a)
    along=(upper*upper-fore*fore+reach*reach)/(2.*reach)
    radius=np.sqrt(max(0.,upper*upper-along*along))
    pole=axis_angle(direction,phi_start*(1.-w))@between(reach0,direction)@pole0
    e=a+direction*along+pole*radius;u=e-a;f=h-e;normal=unit(np.cross(u,f))
    uq=frame(u,normal)@Bu.T@ru;lq=frame(f,normal)@Bl.T@rl
    hq=hand_q0@R.from_rotvec(hand_rot(dt)).as_matrix()
    delta=lq.T@hq@neutral.T;turn=twist(delta,axis)
    swing=R.from_matrix(delta@axis_angle(axis,-turn)).as_rotvec()
    swing*=min(1.,np.radians(32.)/max(np.linalg.norm(swing),1.e-9))
    hq=lq@R.from_rotvec(swing).as_matrix()@axis_angle(axis,turn)@neutral
    old_hand=pose[lh].copy()
    pose[lu]=make(a,uq,scale(idle[lu]));pose[ll]=make(e,lq,scale(idle[ll]));pose[lh]=make(h,hq,scale(idle[lh]))
    hand_delta=pose[lh]@np.linalg.inv(old_hand)
    for n in names:
        if n.endswith('_l') and n.split('_')[0] in ['thumb','index','middle','ring','pinky']:pose[n]=hand_delta@pose[n]
    # Rebuild helpers from both actual forearms, retaining the V9 distribution.
    for side in ['l','r']:
        U,L,H='upperarm_'+side,'lowerarm_'+side,'hand_'+side
        lq=rotation(pose[L]);idle_lq=rotation(idle[L]);idle_rel=idle_lq.T@rotation(idle[H])
        local_axis=idle_lq.T@unit(idle[H][:3,3]-idle[L][:3,3])
        tau=twist(lq.T@rotation(pose[H])@idle_rel.T,local_axis)
        for suffix,share in [('01',1.),('02',.5)]:
            n='upperarm_twist_'+suffix+'_'+side;pose[n]=pose[U]@np.linalg.inv(idle[U])@idle[n]
            n='lowerarm_twist_'+suffix+'_'+side;m=np.linalg.inv(idle[L])@idle[n]
            pose[n]=make((pose[L]@np.r_[m[:3,3],1.])[:3],lq@axis_angle(local_axis,tau*share)@rotation(m),scale(idle[n]))
    grip=make(grip0[:3,3]*(1.-w)+grip1[:3,3]*w,blend(rotation(grip0),rotation(grip1),w),scale(grip1))
    pose['WPN_root']=pose['hand_r']@np.linalg.inv(grip)
    rows.append(pose)
rows[-1]={n:m.copy() for n,m in idle.items()}
out=P/variant;out.mkdir(exist_ok=True)
(out/'poses.json').write_text(json.dumps(dict(variant=variant,fps=FPS,seconds=END,names=names,
    poses=[[row[n].tolist() for n in names] for row in rows]),separators=(',',':')))
source=json.loads((P.parent/'FirstMotionV6/first-version.json').read_text());native_idle_world={}
for n,v in zip(source['names'],source['variants'][variant]['idle']):
    native_idle_world[n]=native_idle_world.get(source['parents'][n],np.eye(4))@mat(v)
tracks={n:[] for n in names};previous={}
for row in rows:
    world={n:AI@row[n]@np.linalg.inv(rest[n])@A@nrest[n] for n in names}
    for n in names:
        pn=source['parents'][n];m=np.linalg.inv(world.get(pn,native_idle_world.get(pn,np.eye(4))))@world[n]
        q=R.from_matrix(rotation(m)).as_quat()
        if n in previous and previous[n]@q<0:q=-q
        previous[n]=q;tracks[n].append(dict(p=m[:3,3].tolist(),q=q.tolist(),s=scale(m).tolist()))
(out/'tracks.json').write_text(json.dumps(dict(fps=FPS,seconds=END,tracks=tracks),separators=(',',':')))
print('DIRECT_RECOVERY_AUTHORED',variant,'preserved_prefix',START,'return',SPAN,'duration',END)
