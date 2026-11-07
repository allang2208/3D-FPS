"""Author independent full-body Highland takes with a rigid two-hand grip.

Inputs are the installed body bind, native ready/landing primary joints, and
the actual equipment palm mounts captured in the preceding requested review.
No first-person arm rotations are copied into the body.
"""
from pathlib import Path
import json, math, hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
from scipy.optimize import minimize_scalar

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
CAPTURE=ROOT/'Saved/HighlandThirdPersonReview20261106/native-v3'
FPS=120

def unit(a):
    return a/max(1e-10,np.linalg.norm(a))

def rot(m):
    return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)

def mat(row):
    m=np.eye(4);m[:3,3]=row[:3];m[:3,:3]=R.from_quat(row[3:7]).as_matrix()*row[7:10]
    return m

def rigid(p,r):
    m=np.eye(4);m[:3,3]=p;m[:3,:3]=r
    return m

def pack(m):
    return [*m[:3,3],*R.from_matrix(rot(m)).as_quat(),*np.linalg.norm(m[:3,:3],axis=0)]

def smooth(t):
    t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))

def mix(a,b,t):
    ar=rot(a);out=rigid(a[:3,3]*(1-t)+b[:3,3]*t,ar@R.from_rotvec(R.from_matrix(ar.T@rot(b)).as_rotvec()*t).as_matrix())
    out[:3,:3]*=(1-t)*np.linalg.norm(a[:3,:3],axis=0)+t*np.linalg.norm(b[:3,:3],axis=0)
    return out

def between(a,b):
    a,b=unit(a),unit(b);q=np.r_[np.cross(a,b),1+a@b]
    if np.linalg.norm(q)<1e-8:
        axis=unit(np.cross(a,[0,0,1] if abs(a[2])<.8 else [0,1,0]));return R.from_rotvec(axis*np.pi).as_matrix()
    return R.from_quat(q).as_matrix()

def basis(direction,normal):
    x=unit(direction);z=unit(normal-x*(x@normal));return np.column_stack((x,np.cross(z,x),z))

def fk(local,parents):
    result=[]
    for i,p in enumerate(parents):result.append(result[p]@local[i] if p>=0 else local[i].copy())
    return result

def to_local(world,parents):
    return [np.linalg.inv(world[p])@v if p>=0 else v.copy() for p,v in zip(parents,world)]

def primary(name):
    return name in ['root','pelvis','head','hand_r','hand_l','clavicle_r','clavicle_l'] or (
        name.startswith(('spine_','neck_','upperarm_','lowerarm_','thigh_','calf_','foot_','ball_',
                         'thumb_','index_','middle_','ring_','pinky_','ik_'))
        and not any(s in name for s in ['twist','corrective','_half_','_correct','_bck','_fwd','_in_','_out_']))

def inputs(kind,grip):
    out=P/'Inputs'/f'{kind}-{grip}.json'
    if not out.exists():
        meta=json.loads((CAPTURE/kind/'mesh.json').read_text(encoding='utf-8-sig'))
        ready=CAPTURE/kind/(grip+'_charged_thrust')
        land=CAPTURE/kind/(grip+'_sweep')
        move=json.loads((ready/'motion.json').read_text(encoding='utf-8-sig'))
        count=len(meta['names'])
        a=np.fromfile(ready/'poses.bin',np.float32).reshape(-1,count,10)[-1]
        b=np.fromfile(land/'poses.bin',np.float32).reshape(-1,count,10)[6]
        info=dict(mesh=meta['mesh'],names=meta['names'],parents=meta['parents'],rest=meta['rest'],
                  ready=a.tolist(),land=b.tolist(),mount=move['mount'],left_grip=move['left_grip'],
                  provenance=str(CAPTURE),ready_sha256=hashlib.sha256((ready/'poses.bin').read_bytes()).hexdigest())
        out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(info,separators=(',',':')))
    return json.loads(out.read_text())

class Rig:
    def __init__(self,data):
        self.data=data;self.names=data['names'];self.parents=data['parents'];self.ids={n:i for i,n in enumerate(self.names)}
        self.ref=[mat(v) for v in data['rest']];self.ref_local=to_local(self.ref,self.parents)
        self.ready=self.clean([mat(v) for v in data['ready']]);self.land=self.clean([mat(v) for v in data['land']])
        self.ready_local=to_local(self.ready,self.parents);self.land_local=to_local(self.land,self.parents)
        self.mount=mat(data['mount']);self.grips={'r':np.linalg.inv(self.mount),'l':np.linalg.inv(self.mount)@mat(data['left_grip'])}
        self.weapon_ready=self.ready[self.ids['hand_r']]@self.mount
        self.weapon_land=self.land[self.ids['hand_r']]@self.mount
        self.previous_pole={};self.previous_twist={}
        self.shoulders=np.mean([self.ready[self.ids['upperarm_'+s]][:3,3] for s in ['r','l']],axis=0)
        self.stats=[]

    def clean(self,world):
        local=to_local(world,self.parents)
        # Post-process corrective results are not baked twice. The runtime body
        # post-process continues to own auxiliary deformation bones.
        local=[m if primary(n) else self.ref_local[i].copy() for i,(n,m) in enumerate(zip(self.names,local))]
        return fk(local,self.parents)

    def children(self,pose,local,roots):
        affected=set(roots)
        for i,p in enumerate(self.parents):
            if p in affected:
                affected.add(i)
                if i not in roots:pose[i]=pose[p]@local[i]
        return affected

    def arm(self,pose,base,local,side,target,record=False):
        u,e,h=[self.ids[n+'_'+side] for n in ['upperarm','lowerarm','hand']]
        A,E,W=[base[i][:3,3] for i in [u,e,h]];T=target[:3,3]
        a,b=np.linalg.norm(E-A),np.linalg.norm(W-E);axis=unit(T-A);d=np.linalg.norm(T-A)
        if d>(a+b)*.985:
            # Move the clavicle only within a small anatomical reach allowance.
            amount=d-(a+b)*.985
            if amount>2.0:raise RuntimeError(f'Unreachable {side} target by {amount:.2f} cm')
            c=self.ids['clavicle_'+side];pose[c]=base[c].copy();pose[c][:3,3]+=axis*amount
            A=A+axis*amount;d=np.linalg.norm(T-A)
        along=(a*a-b*b+d*d)/(2*d);height=math.sqrt(max(0.,a*a-along*along))
        chest=self.ids['spine_03']
        guide=rot(base[chest])@rot(self.ready[chest]).T@np.array([-1 if side=='r' else 1,-.08,-1.2])
        pole=unit(guide-axis*(guide@axis));other=unit(np.cross(axis,pole))
        neutral_hand=self.ref_local[h][:3,:3]
        lower_axis=unit(self.ref_local[h][:3,3])
        desired=rot(target)@neutral_hand.T@lower_axis
        natural=pole.copy()
        last=self.previous_pole.get(side,pole)
        def point(phi):return A+along*axis+height*(math.cos(phi)*pole+math.sin(phi)*other)
        def score(phi):
            arm=unit(T-point(phi));p=math.cos(phi)*pole+math.sin(phi)*other
            flex=1-np.clip(arm@desired,-1,1)
            high=max(0.,point(phi)[2]-(A[2]-2))/a
            return 5.0*flex+.3*(1-p@natural)+.2*(1-p@last)+10*high*high
        # Bound the transported elbow plane, rather than optimizing an unlimited
        # pole that can jump across the body or flip between equivalent solves.
        search=minimize_scalar(score,bounds=(-1.8,1.8),method='bounded',options={'xatol':1e-6})
        elbow=point(search.x);newpole=unit(elbow-A-axis*((elbow-A)@axis));self.previous_pole[side]=newpole
        n0=unit(np.cross(E-base[u][:3,3],W-E));n=unit(np.cross(elbow-A,T-elbow))
        du=basis(elbow-A,n)@basis(E-base[u][:3,3],n0).T
        dl=between(du@(W-E),T-elbow)@du
        pose[u]=rigid(A,du@rot(base[u]));pose[e]=rigid(elbow,dl@rot(base[e]));pose[h]=target
        affected=self.children(pose,local,{u,e,h})
        axis_fore=unit(T-elbow)
        nominal=rot(pose[e])@neutral_hand
        delta=R.from_matrix(rot(target)@nominal.T).as_quat()
        angle=2*math.atan2(delta[:3]@axis_fore,delta[3])
        last_twist=self.previous_twist.get(side,0.)
        angle=last_twist+(angle-last_twist+np.pi)%(2*np.pi)-np.pi
        self.previous_twist[side]=angle
        for i in affected:
            n=self.names[i]
            if n.startswith('lowerarm_twist_') and n.endswith('_'+side):
                portion=1. if '_01_' in n else .5
                pose[i][:3,:3]=R.from_rotvec(axis_fore*angle*portion).as_matrix()@pose[i][:3,:3]
        if record:self.stats.append(dict(side=side,flex=float(np.degrees(np.arccos(np.clip(unit(T-elbow)@desired,-1,1)))),twist=float(np.degrees(angle)),reach=d/(a+b)))

    def torso(self,local,yaw,lean,shift):
        local=[v.copy() for v in local]
        world=fk(local,self.parents)
        pelvis=self.ids['pelvis'];world[pelvis][:3,3]+=shift
        local[pelvis]=np.linalg.inv(world[self.parents[pelvis]])@world[pelvis]
        for name in ['spine_01','spine_02','spine_03']:
            world=fk(local,self.parents);i=self.ids[name];p=self.parents[i]
            turn=R.from_euler('xz',[-lean/3,yaw/3],degrees=True).as_matrix()
            local[i][:3,:3]=rot(world[p]).T@turn@rot(world[p])@local[i][:3,:3]
        return local

    def legs(self,pose,base,local,targets):
        for side in ['r','l']:
            u,e,h=[self.ids[n+'_'+side] for n in ['thigh','calf','foot']]
            A,E,W=[base[i][:3,3] for i in [u,e,h]];target=targets[side];T=target[:3,3]
            a,b=np.linalg.norm(E-A),np.linalg.norm(W-E);axis=unit(T-A);d=min(np.linalg.norm(T-A),(a+b)*.995)
            T=A+axis*d;along=(a*a-b*b+d*d)/(2*d)
            old=unit(W-A);pole=unit(between(old,axis)@unit(E-A-old*((E-A)@old)))
            knee=A+axis*along+pole*math.sqrt(max(0,a*a-along*along))
            du=between(E-A,knee-A);dl=between(du@(W-E),T-knee)@du
            pose[u]=rigid(A,du@rot(base[u]));pose[e]=rigid(knee,dl@rot(base[e]));pose[h]=rigid(T,rot(target))
            self.children(pose,local,{u,e,h})

def weapon_frame(yaw,elevation,roll):
    a,b=np.radians([yaw,elevation]);z=np.array([-math.sin(a)*math.cos(b),math.cos(a)*math.cos(b),math.sin(b)])
    x=np.array([math.cos(a),math.sin(a),0.]);return np.column_stack((x,np.cross(z,x),z))@R.from_euler('z',roll,degrees=True).as_matrix()

def weapon(rig,xyz,yaw=0,elevation=0,roll=0):
    return rigid(rig.shoulders+np.array(xyz),weapon_frame(yaw,elevation,roll))

def scene(rig,role,t,roll):
    if role=='RidgeThrust':
        load=smooth(t/(40/120));release=smooth((t-40/120)/(8/120));recover=smooth((t-84/120)/(108/120))
        loaded=weapon(rig,[-12,26,-29],0,3,roll)
        extended=weapon(rig,[-2,54,-23],0,0,roll)
        w=mix(rig.weapon_ready,loaded,load)
        if t>=40/120:w=mix(loaded,extended,release)
        w=mix(w,rig.weapon_ready,recover)
        power=release*(1-recover);coil=load*(1-release)
        local=rig.torso(rig.ready_local,8*coil-3*power,4*coil+9*power,np.array([0.,3*power,-1.5*power]))
        feet={s:rig.ready[rig.ids['foot_'+s]] for s in ['r','l']}
    else:
        prep=smooth(t/.30);stroke=smooth((t-.30)/.17);brake=smooth((t-.47)/.16);back=smooth((t-.68)/(4/3-.68))
        yaw=65-130*stroke-10*brake
        if role=='SweepReady':local=[v.copy() for v in rig.ready_local]
        else:
            rise=.7*prep+.3*back
            local=[mix(a,b,rise) for a,b in zip(rig.land_local,rig.ready_local)]
            current=fk(local,rig.parents);sp=rig.ids['spine_01'];parent=rig.parents[sp]
            upright=local[sp].copy();upright[:3,:3]=rot(current[parent]).T@rot(rig.ready[sp])
            local[sp]=mix(local[sp],upright,prep)
        local=rig.torso(local,(45-90*stroke)*prep*(1-back),4*prep*(1-back),np.zeros(3))
        current=fk(local,rig.parents)
        shoulders=np.mean([current[rig.ids['upperarm_'+s]][:3,3] for s in ['r','l']],axis=0)
        lateral=current[rig.ids['upperarm_l']][:3,3]-current[rig.ids['upperarm_r']][:3,3]
        lateral=unit(np.array([lateral[0],lateral[1],0.]))
        forward=np.cross([0,0,1.],lateral)
        point=shoulders+lateral*(-8+17*stroke)+forward*(40+3*math.sin(np.pi*stroke))+np.array([0,0,-27-2*stroke])
        strike=rigid(point,weapon_frame(yaw,3-6*stroke,roll))
        begin=rig.weapon_ready if role=='SweepReady' else rig.weapon_land
        w=mix(begin,strike,prep) if t<.30 else strike
        if role=='Sweep' and t<.30:w[:3,3]+=np.array([0,10*math.sin(np.pi*prep),0])
        w=mix(w,rig.weapon_ready,back)
        feet={s:mix((rig.ready if role=='SweepReady' else rig.land)[rig.ids['foot_'+s]],rig.ready[rig.ids['foot_'+s]],back) for s in ['r','l']}
    base=fk(local,rig.parents);pose=[v.copy() for v in base]
    # Fit the rigid sword/palm group to both arms together. Small reach limits
    # adjust the hilt path, never stretch the skeleton or detach one support hand.
    for _ in range(8):
        for side in ['r','l']:
            u,e,h=[rig.ids[n+'_'+side] for n in ['upperarm','lowerarm','hand']]
            a=base[u][:3,3];length=np.linalg.norm(base[e][:3,3]-a)+np.linalg.norm(base[h][:3,3]-base[e][:3,3])
            target=(w@rig.grips[side])[:3,3];d=np.linalg.norm(target-a)
            if d>length*.96:w[:3,3]-=unit(target-a)*(d-length*.96)
            if d<length*.30:w[:3,3]+=np.array([0.,length*.30-d,0.])
    rig.legs(pose,base,local,feet)
    for side in ['r','l']:rig.arm(pose,base,local,side,w@rig.grips[side],True)
    for side in ['r','l']:
        hand,ik=rig.ids['hand_'+side],rig.ids.get('ik_hand_'+side)
        if ik is not None:pose[ik]=pose[hand]@np.linalg.inv(base[hand])@base[ik]
    return pose,w

def choose_roll(data,role):
    # A single blade roll is selected for the whole action. It never changes
    # discontinuously to chase a numerically equivalent wrist orientation.
    best=None
    for roll in range(-180,181,15):
        rig=Rig(data);cost=0
        try:
            for t in ([.30,.36,.4,.7] if role=='RidgeThrust' else [.30,.35,.40,.47,.60]):
                scene(rig,role,t,roll)
            for s in rig.stats:cost+=s['flex']**2+.05*s['twist']**2
        except RuntimeError:cost=float('inf')
        if best is None or cost<best[0]:best=(cost,roll)
    if not np.isfinite(best[0]):raise RuntimeError('No reachable blade placement')
    return best[1]

def author(kind,grip,role):
    data=inputs(kind,grip);rig=Rig(data);roll=choose_roll(data,role)
    length=1.6 if role=='RidgeThrust' else 4/3
    tracks={n:[] for n in rig.names};worlds=[];weapons=[];prev={}
    for frame in range(round(length*FPS)+1):
        pose,w=scene(rig,role,frame/FPS,roll)
        # End at the equipped ready targets, with both palms still on the hilt.
        local=to_local(pose,rig.parents)
        for n,m in zip(rig.names,local):
            v=pack(m);q=np.array(v[3:7])
            if n in prev and q@prev[n]<0:q=-q
            prev[n]=q;v[3:7]=q.tolist();tracks[n].append(v)
        worlds.append([pack(m) for m in pose]);weapons.append(pack(w))
    stem=f'{kind}_{grip}_{role}'
    (P/(stem+'.json')).write_text(json.dumps(dict(mesh=data['mesh'],fps=FPS,length=length,role=role,tracks=tracks),separators=(',',':')))
    out=P/'Authoring'/stem;out.mkdir(parents=True,exist_ok=True)
    np.array(worlds,dtype=np.float32).tofile(out/'poses.bin')
    (out/'motion.json').write_text(json.dumps(dict(kind=kind,grip=grip,role=role,roll=roll,fps=FPS,weapons=weapons),separators=(',',':')))
    print(stem,'roll',roll,'max flex',round(max(s['flex'] for s in rig.stats),1),'max reach',round(max(s['reach'] for s in rig.stats),3),flush=True)

if __name__=='__main__':
    manifest={}
    for kind in ['Jason','Kaitlin']:
        for grip in ['Standard','LongGrip']:
            for role in ['RidgeThrust','Sweep','SweepReady']:
                author(kind,grip,role)
                filename=f'{kind}_{grip}_{role}.json'
                manifest[filename]=hashlib.sha256((P/filename).read_bytes()).hexdigest()
    (P/'authored-manifest.json').write_text(json.dumps(dict(files=manifest,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
