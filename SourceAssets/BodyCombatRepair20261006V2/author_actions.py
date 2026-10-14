"""Rebuild rejected sword skills around the accepted two-hand carry anatomy.

The rejected heavy-combo crop rolls individual joints by up to 178 degrees per
frame. Reuse the existing Kevin two-hand stance and project pivot helpers, but author
bounded skill paths and a continuous coupled arm solve instead of that crop.
"""
import importlib.util
import json
import math
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('rig',OUT.parent/'ThirdPersonSwordDonorRepair20261006/adapt_donor.py')
rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
names,parents,ix,ref=rig.names,rig.parents,rig.ix,rig.ref
# Evaluate each hierarchy level as a batch while fitting the offline curves.
depth=[]
for p in parents:depth.append(depth[p]+1 if p>=0 else 0)
levels=[np.flatnonzero(np.array(depth)==d) for d in range(1,max(depth)+1)]
parent_array=np.array(parents)
def fast_fk(f):
    w=f.copy()
    for ids in levels:
        p=parent_array[ids];a=w[p,3:7];b=f[ids,3:7];v=f[ids,:3]*w[p,7:]
        uv=np.cross(a[:,:3],v)
        w[ids,:3]=w[p,:3]+v+2*(a[:,3,None]*uv+np.cross(a[:,:3],uv))
        w[ids,3:6]=a[:,3,None]*b[:,:3]+b[:,3,None]*a[:,:3]+np.cross(a[:,:3],b[:,:3])
        w[ids,6]=a[:,3]*b[:,3]-np.sum(a[:,:3]*b[:,:3],axis=1)
        w[ids,7:]=w[p,7:]*f[ids,7:]
    return w
rig.fk=fast_fk
idle=rig.idle.copy();hip=idle[ix['pelvis'],:3].copy()
idle[:,:3]=ref[:,:3];idle[:,7:]=ref[:,7:];idle[ix['pelvis'],:3]=hip
idle_w=rig.fk(idle);weapon_idle=rig.weapon(idle)
grips=rig.grips;bind=rig.bind
# Reuse only the foot-authoring helpers, without executing the old publisher.
leg_path=ROOT/'Tools/PlayerBody/author_whirlwind_jason.py'
leg={"__file__":str(leg_path)}
exec(compile(leg_path.read_text().split('loop_entry = loop_pose')[0],str(leg_path),'exec'),leg)

def swing_frame(theta,rising=False):
    a=math.radians(theta);z=np.array([0,math.sin(a),math.cos(a)])
    edge=np.array([0,math.cos(a),-math.sin(a)])*(-1 if rising else 1)
    x=-edge;y=np.cross(z,x)
    return R.from_matrix(np.column_stack((x,y,z))).as_quat()

def body(load,cut=0.,coil=0.):
    f=idle.copy();f[:,:3]=ref[:,:3];f[:,7:]=ref[:,7:]
    f[ix['root']]=idle[ix['root']];f[ix['pelvis'],:3]=idle[ix['pelvis'],:3]+[0,0,-2.5*load]
    # Small whole-chain effort. No donor root heading, bone translation or scale
    # is pasted onto a pelvis whose forward direction belongs to locomotion.
    for bone,angle in [('spine_01',-3*load+6*cut),('spine_03',-2*load+4*cut)]:
        w=rig.fk(f);j=ix[bone]
        q=rig.mul(rig.axis([0,0,1],math.radians(coil*.5)),rig.mul(rig.axis([1,0,0],math.radians(angle)),w[j,3:7]))
        rig.set_world_q(f,j,q,w)
    return f

class Arms:
    def __init__(self):self.twist={};self.bend={};self.effort=0.;self.shift=np.zeros(3)
    def solve(self,f,side,target):
        a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        w=rig.fk(f);origin=w[a,:3]
        l1,l2=np.linalg.norm(ref[b,:3]),np.linalg.norm(ref[c,:3])
        axis=rig.unit(target[:3]-origin);distance=np.clip(np.linalg.norm(target[:3]-origin),abs(l1-l2)+.01,(l1+l2)*.965)
        end=origin+axis*distance
        # Keep the elbow outside/below its own shoulder throughout vertical cuts.
        # This does not inherit a cross-body donor pole that flips through zero.
        carry=rig.unit(idle_w[b,:3]-idle_w[a,:3])
        hint=carry*(1-self.effort)+rig.unit(np.array([-.8 if side=='r' else .8,.1,-1.]))*self.effort
        bend=hint-axis*np.dot(hint,axis)
        if np.linalg.norm(bend)<.12:
            previous=self.bend.get(side,np.array([0,1.,0]))
            bend=previous-axis*np.dot(previous,axis)
        bend=rig.unit(bend)
        # Swivel the elbow toward the forearm direction implied by the grip.
        # A fixed outward pole can require a 180-degree wrist fold when the
        # blade becomes horizontal, where swing/twist decomposition is singular.
        ideal_lower=rig.rot(rig.mul(target[3:7],rig.inv(ref[c,3:7])),rig.unit(ref[c,:3]))
        wanted=end-ideal_lower*l2-origin
        wanted-=axis*np.dot(wanted,axis)
        desired=rig.unit(wanted)
        # Interpolate the swivel angle, not opposite pole vectors through zero.
        prior=self.bend.get(side,bend);prior=rig.unit(prior-axis*np.dot(prior,axis))
        angle=math.atan2(np.dot(axis,np.cross(prior,desired)),np.dot(prior,desired))
        angle=np.clip(angle,-math.radians(18),math.radians(18))
        bend=rig.rot(rig.axis(axis,angle),prior)
        self.bend[side]=bend
        along=(l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow=origin+axis*along+bend*math.sqrt(max(0,l1*l1-along*along))
        normal=rig.unit(np.cross(elbow-origin,end-elbow))
        old1,old2=idle_w[b,:3]-idle_w[a,:3],idle_w[c,:3]-idle_w[b,:3]
        oldnormal=rig.unit(np.cross(old1,old2))
        for bone,old,new in [(a,old1,elbow-origin),(b,old2,end-elbow)]:
            q=rig.mul(rig.mul(rig.frame_xy(new,normal),rig.inv(rig.frame_xy(old,oldnormal))),idle_w[bone,3:7])
            rig.set_world_q(f,bone,q,rig.fk(f))
        w=rig.fk(f);neutral=rig.mul(w[b,3:7],ref[c,3:7])
        diff=rig.mul(target[3:7],rig.inv(neutral));forearm=rig.unit(end-elbow)
        twist=2*math.atan2(np.dot(diff[:3],forearm),diff[3])
        prior=self.twist.get(side,0.)
        twist+=round((prior-twist)/(2*math.pi))*2*math.pi
        if side in self.twist:twist=np.clip(twist,prior-math.radians(16),prior+math.radians(16))
        self.twist[side]=twist
        # Full pronation is continuous across +/-pi. Multiplying a wrapped angle
        # by .8 was producing a discontinuous 288-degree forearm correction.
        rig.set_world_q(f,b,rig.mul(rig.axis(forearm,twist),w[b,3:7]),w)
        rig.set_world_q(f,c,target[3:7],rig.fk(f))
    def fit(self,f,wp):
        rotation=(R.from_quat(weapon_idle[3:7]).inv()*R.from_quat(wp[3:7])).magnitude()
        self.effort=rig.smooth(max(np.linalg.norm(wp[:3]-weapon_idle[:3])/24.,rotation/1.2))
        goals={s:rig.compose(wp,grips[s]) for s in ('r','l')};w=rig.fk(f)
        anatomy=[]
        for s in ('r','l'):
            a,b,c=[ix[n+'_'+s] for n in ('upperarm','lowerarm','hand')]
            ideal=rig.rot(rig.mul(goals[s][3:7],rig.inv(ref[c,3:7])),rig.unit(ref[c,:3]))
            anatomy.append((w[a,:3],goals[s][:3],np.linalg.norm(ref[b,:3]),np.linalg.norm(ref[c,:3]),ideal))
        def fit_hilt(shift):
            errors=list(shift/16)
            for origin,goal,l1,l2,ideal in anatomy:
                wrist=goal+shift;axis=rig.unit(wrist-origin);d=np.linalg.norm(wrist-origin)
                along=(l1*l1-l2*l2+d*d)/(2*max(d,.01));radius=math.sqrt(max(0,l1*l1-along*along))
                center=origin+axis*along;wanted=wrist-ideal*l2-center;wanted-=axis*np.dot(wanted,axis)
                elbow=center+rig.unit(wanted)*radius
                cosine=np.dot(rig.unit(wrist-elbow),ideal)
                errors.extend([max(0,d-(l1+l2)*.955),max(0,20-d),max(0,math.cos(math.radians(48))-cosine)*8])
            return errors
        shift=least_squares(fit_hilt,self.shift,max_nfev=50).x;self.shift=shift.copy()
        for _ in range(16):
            for s in ('r','l'):
                center=w[ix['upperarm_'+s],:3]
                radius=.955*sum(np.linalg.norm(ref[ix[n+'_'+s],:3]) for n in ('lowerarm','hand'))
                delta=goals[s][:3]+shift-center
                if np.linalg.norm(delta)>radius:shift-=rig.unit(delta)*(np.linalg.norm(delta)-radius)
        for s in ('r','l'):
            goal=goals[s].copy();goal[:3]+=shift;self.solve(f,s,goal)
        return f

def make_clip(label,duration,keys,contact,release,rising=False):
    # Keys: phase, hilt xyz, blade angle. PCHIP keeps the hilt inside its authored
    # reach envelope; shortest-arc eased rotations avoid blade-axis flips.
    times=np.array([k[0] for k in keys]);positions=np.array([k[1] for k in keys])
    positions[0]=positions[-1]=weapon_idle[:3]
    curve=PchipInterpolator(times,positions)
    rotations=[weapon_idle[3:7] if j in (0,len(keys)-1) else swing_frame(k[2],rising) for j,k in enumerate(keys)]
    arm=Arms();frames=[];count=round(duration*30)
    # Settle the initial grip before sampling; the first authored frame must not
    # contain an iterative IK startup transient.
    for _ in range(18):carry=arm.fit(body(0),weapon_idle)
    def solve_at(p,solver):
        span=min(np.searchsorted(times,p,side='right')-1,len(times)-2)
        blend=rig.smooth((p-times[span])/(times[span+1]-times[span]))
        wp=np.r_[curve(p),rig.slerp(rotations[span],rotations[span+1],blend)]
        load=rig.smooth(p/contact)*(1-rig.smooth((p-contact)/max(.01,release-contact)))
        cut=rig.smooth((p-contact)/max(.01,release-contact))*(1-rig.smooth((p-release)/(1-release)))
        return solver.fit(body(load,cut,-5*load+4*cut),wp)
    ready_solver=Arms();arm=Arms()
    for _ in range(18):
        ready=solve_at(times[1],ready_solver)
        contact_pose=solve_at(contact,arm)
    ready_frame=round(times[1]*count);contact_frame=round(contact*count)
    release_frame=round(release*count)
    for i in range(count+1):
        if i<=ready_frame:
            frames.append(rig.blend(carry,ready,rig.smooth(i/ready_frame)));continue
        if i<=contact_frame:
            frames.append(rig.blend(ready,contact_pose,rig.smooth((i-ready_frame)/(contact_frame-ready_frame))));continue
        if i>release_frame:
            # Return through the solved arm pose. Rotating the hilt directly
            # back to idle makes the wrist/pole solver choose another branch.
            frames.append(rig.blend(frames[release_frame],carry,rig.smooth((i-release_frame)/(count-release_frame))))
            continue
        frames.append(solve_at(i/count,arm))
    frames[0]=carry;frames[-1]=carry.copy()
    return dict(rate=30,contact=contact,release=release,frames=np.array(frames).tolist())

clips={}
for label,duration in [('DashOverhead',1.5),('Overhead',1.9)]:
    clips[label]=make_clip(label,duration,[
        (0,[0,0,0],0),(.25,[-18,34,142],55),(.36,[-18,38,143],65),
        (.57,[-18,49,121],103),(.69,[-18,46,104],130),(.82,[-20,43,98],118),(1,[0,0,0],0)],.36,.69)
clips['Uppercut']=make_clip('Uppercut',1.8,[
    (0,[0,0,0],0),(.25,[-10,39,94],143),(.36,[-8,43,93],138),
    (.60,[-7,51,121],55),(.71,[-9,42,142],-12),(.84,[-15,39,130],5),(1,[0,0,0],0)],.36,.71,True)

z=rig.unit(np.array([.86,.51,.015]));edge=rig.unit(np.cross([0,0,-1],z));x=-edge
spin_q=R.from_matrix(np.column_stack((x,np.cross(z,x),z))).as_quat()
spin_wp=np.r_[[-10,40,115],spin_q]
arm=Arms();phases={}
for repeat in range(3):
    frames=[]
    for i in range(37):
        p=i/36;f=body(.35,0.,0.)
        f[ix['pelvis'],:3]+=[1.4*math.sin(2*math.pi*p),0,-.6*math.sin(2*math.pi*p)**2]
        targets={side:leg['foot_cycle'](p,side) for side in (-1,1)}
        f=leg['legs'](f,targets);frames.append(arm.fit(f,spin_wp))
    phases['Loop']=np.array(frames)
# Blend complete anatomical poses into the settled loop, instead of forcing the
# wrists through a straight quaternion path that folds one palm backward.
carry_arm=Arms()
for _ in range(16):carry=carry_arm.fit(body(0),weapon_idle)
for label,count in [('Start',18),('End',24)]:
    phases[label]=np.array([rig.blend(carry,phases['Loop'][0],rig.smooth(i/count) if label=='Start' else 1-rig.smooth(i/count)) for i in range(count+1)])
# Shared joints and feet match at phase boundaries; no root rotation is baked.
phases['Loop'][-1]=phases['Loop'][0]
phases['Start'][-1]=phases['Loop'][0];phases['End'][0]=phases['Loop'][0]
for label,f in phases.items():clips['Whirlwind.'+label]=dict(rate=30,frames=f.tolist(),contact=.35,release=.7)
for c in clips.values():
    f=np.array(c['frames'])
    for i in range(1,len(f)):
        flip=np.sum(f[i-1,:,3:7]*f[i,:,3:7],axis=1)<0;f[i,flip,3:7]*=-1
    c['frames']=f.tolist()
result=dict(mesh=rig.base['mesh'],skeleton=rig.base['skeleton'],names=names,clips=clips,
    provenance='Existing project Kevin two-hand carry and authored two-step pivot; new bounded skill paths and paired-arm fitting at fixed Jason bone lengths',
    source_inputs=['SourceAssets/ThirdPersonSwordActions20261006/authoring-input.json','Tools/PlayerBody/author_whirlwind_jason.py'])
(OUT/'authored-actions.json').write_text(json.dumps(result,separators=(',',':')))
print('BODY_COMBAT_REAUTHORED '+', '.join(clips))
