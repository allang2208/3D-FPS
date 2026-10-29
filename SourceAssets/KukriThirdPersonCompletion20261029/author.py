"""Complete native third-person Kukri branches using current saved poses.

The FPS actions supply clocks and palm intent; native bodies supply bone lengths,
support and fingers. Blade flight is authored with the hands, in mount space.
"""
import importlib.util, json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R, Slerp

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]; RATE=120
def module(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('completion_native','SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
solver=module('completion_solver','SourceAssets/PistolKukriThrustBody20261029/author.py')
c=old.c; M=np.diag([-1.,1.,1.]); C=R.from_euler('z',90,degrees=True)

def phase(t,a,b):return c.ease((t-a)/(b-a))
def clock(length):return np.linspace(0,length,round(length*RATE)+1)
def curve(t,keys,values):return PchipInterpolator(keys,np.array(values))(t)
def sample(take,t):return np.array([c.sample(np.array(take['frames']),x,take['rate']) for x in t])
def fingers(body,f,pose,side,w=1.):
    for i,n in enumerate(body.names):
        if n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_')):
            f[:,i,3:7]=c.slerp(f[:,i,3:7],np.broadcast_to(pose[i,3:7],(len(f),4)),np.asarray(w)[...,None])
def arm(body,f,side,offset,poleoffset,roll,t,weight):
    p,q=body.world(f);ip,iq=body.world(body.idle)
    u,e,h=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    chest=body.ix['spine_05'];tr=R.from_quat(q[:,chest])*R.from_quat(iq[chest]).inv()
    goal=p[:,u]+tr.apply(np.tile(ip[h]-ip[u],(len(t),1))+offset)
    pole=p[:,u]+tr.apply(np.tile(ip[e]-ip[u],(len(t),1))+poleoffset)
    hand=tr*R.from_rotvec(roll)*R.from_quat(iq[h])
    solver.T=t;solver.solve_arm(body,f,side,goal,pole,hand,weight)
def finish(body,f,idle,end=True):
    old.helpers(body,f)
    if end:f[-1]=idle
    return old.carry.continuous(f)
def mounts(body):
    rp,rq=old.base.native.blade_mount(body);_,lp,lq=old.carry.dual.v1.left_grip(body)
    return {'r':(rp,rq),'l':(lp,lq)}
def delta_mount(p,q,bp,bq):
    return np.c_[bq.inv().apply(p-bp),(bq.inv()*q).as_quat()]
def shoulder_scale(body):
    return (np.linalg.norm(body.ref[body.ix['lowerarm_r'],:3])+np.linalg.norm(body.ref[body.ix['hand_r'],:3]))/60.

def equip(body,idle,dual):
    body.idle=idle.copy();length=.92 if dual else .8;t=clock(length);sc=shoulder_scale(body)
    f=np.repeat(idle[None],len(t),axis=0);ms=mounts(body);blades={};times={}
    for side in ('r','l') if dual else ('r',):
        delay=.067 if side=='l' else 0.;release=10/120+delay;catch=52/120+delay
        keys=[0,release,.22+delay,catch,.54+delay,length]
        sign=1 if side=='l' else -1
        offset=curve(t,keys,[[sign*3,-5,-20],[sign*5,3,5],[sign*7,1,-5],[sign*5,3,8],[sign*3,1,-2],[0,0,0]])*sc
        pole=curve(t,keys,[[sign*2,-2,-8],[sign*4,2,0],[sign*5,0,-3],[sign*5,1,1],[sign*3,0,-2],[0,0,0]])*sc
        roll=curve(t,keys,[[-.10,0,0],[.12,0,0],[-.05,0,0],[.06,0,0],[-.025,0,0],[0,0,0]])
        w=1.-phase(t,length-.16,length)
        arm(body,f,side,offset,pole,roll,t,w)
        opened=phase(t,release-.025,release+.025)*(1.-phase(t,catch-.055,catch+.025))
        # Native open reference only relaxes the accepted grip; thumb retains
        # its base opposition and the fingers close before the handle settles.
        fingers(body,f,body.ref,side,.72*opened)
        times[side]=(release,catch)
    if not dual:
        w=np.sin(np.pi*t/length)**2
        arm(body,f,'l',w[:,None]*np.array([3,-2,-3])*sc,w[:,None]*np.array([2,0,-2])*sc,np.zeros((len(t),3)),t,.4*w)
    f=finish(body,f,idle);p,q=body.world(f)
    for side,(release,catch) in times.items():
        bp,bq=ms[side];i=body.ix['hand_'+side];hr=R.from_quat(q[:,i]);wp=p[:,i]+hr.apply(bp);wq=hr*bq
        a=round(release*RATE);b=round(catch*RATE);alpha=np.clip((t-release)/(catch-release),0,1)
        flight=(t>=release)&(t<=catch);s=alpha[flight]
        desired_p=wp.copy();desired_q=wq.as_quat().copy()
        # Ballistic-looking arc stays in the outer/front lane, away from head.
        desired_p[flight]=wp[a]*(1-s[:,None])+wp[b]*s[:,None]+(4*s*(1-s))[:,None]*np.array([0,2,31])*sc
        turn=R.from_rotvec(np.c_[2*np.pi*s,np.zeros((len(s),2))])
        desired_q[flight]=(turn*R.from_quat(c.slerp(wq[a].as_quat(),wq[b].as_quat(),c.ease(s)[:,None]))).as_quat()
        local_p=hr.inv().apply(desired_p-p[:,i]);local_q=hr.inv()*R.from_quat(desired_q)
        blades[side]=delta_mount(local_p,local_q,bp,bq).tolist()
    return f,t,blades,dict(release=10/120,catch=52/120,left_delay=.067 if dual else 0)

def offhand_uppercut(body,d):
    idle=np.array(d['clips']['Pistol.KukriCarry.Hip']['frames'][0]);body.idle=idle.copy()
    src=d['clips']['Kukri.FullBody.Uppercut'];t=clock(1.2666666667)
    st=t/t[-1]*src['duration'];donor=sample(src,st);dp,dq=body.world(donor)
    # Mirror torso/leg world deltas around the native reference, keeping every
    # target segment translation and scale. Arms are solved independently below.
    f=np.repeat(idle[None],len(t),axis=0);world={};ip,iq=body.world(idle)
    for i,n in enumerate(body.names):
        if n=='pelvis' or n.startswith(('spine_','thigh_','calf_','foot_','ball_')):
            pair=n[:-2]+('_l' if n.endswith('_r') else '_r') if n.endswith(('_r','_l')) else n
            j=body.ix.get(pair,i)
            delta=R.from_quat(dq[:,j])*R.from_quat(dq[0,j]).inv()
            mirrored=R.from_matrix(M@delta.as_matrix()@M)
            amount=.45 if n.startswith('spine_') else .65
            world[i]=R.from_rotvec(mirrored.as_rotvec()*amount)*R.from_quat(iq[i])
    body.set_world_rotations(f,world)
    w=phase(t,0,.22)*(1.-phase(t,.95,t[-1]));f=c.blend(np.repeat(idle[None],len(t),axis=0),f,w[:,None,None])
    p,q=body.world(f);ip,iq=body.world(idle);chest=body.ix['spine_05']
    torso=R.from_quat(q[:,chest])*R.from_quat(iq[chest]).inv()
    donor_torso=R.from_quat(dq[:,chest])*R.from_quat(body.tq[chest]).inv()
    sc=shoulder_scale(body)
    raw=json.loads((ROOT/'SourceAssets/DualPistolKukri20261025/Work/upper/offhand_upper_keys.json').read_text())
    kt=np.array([k['t'] for k in raw['keys']]);kq=R.from_matrix(np.array([k['left_hand'] for k in raw['keys']])[:,:3,:3])
    fps=Slerp(kt,kq)(np.clip(t,kt[0],kt[-1]));palm,offset=solver.carry.palm_mount(body,'l')
    u,e,h=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    ul,el,hl=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    reach=donor_torso.inv().apply(dp[:,h]-dp[:,u])@M
    reach[:,0]=np.maximum(reach[:,0]+5*sc,10*sc)
    reach[:,1]=np.maximum(reach[:,1],(17+13*phase(reach[:,2],0,20*sc))*sc)
    elbow=donor_torso.inv().apply(dp[:,e]-dp[:,u])@M
    goal=p[:,ul]+torso.apply((ip[hl]-ip[ul])*(1-w[:,None])+reach*w[:,None])
    pole=p[:,ul]+torso.apply((ip[el]-ip[ul])*(1-w[:,None])+elbow*w[:,None])
    rest=torso*R.from_quat(iq[hl]);hand=R.from_quat(c.slerp(rest.as_quat(),(torso*C*fps*palm.inv()).as_quat(),w[:,None]))
    solver.T=t;solver.solve_arm(body,f,'l',goal,pole,hand,w)
    # The FPS recovery palm is unreachable on the shorter full-body forearm.
    # Relax that palm direction, then solve the WHOLE chain again so the elbow
    # and forearm share the correction instead of leaving a folded wrist.
    for _ in range(2):
        ap,aq=body.world(f);hr=R.from_quat(aq[:,hl])
        axis=(hr*R.from_quat(body.ref[hl,3:7]).inv()).apply(np.tile(c.unit(body.ref[hl,:3]),(len(t),1)))
        fore=c.unit(ap[:,hl]-ap[:,el]);angle=np.arccos(np.clip(np.sum(axis*fore,axis=1),-1,1))
        turn=c.unit(np.cross(axis,fore));correction=gaussian_filter1d(np.maximum(0.,angle-np.radians(48.)),1.3)
        hand=R.from_rotvec(turn*correction[:,None])*hr
        solver.solve_arm(body,f,'l',goal,pole,hand,w)
    gun=phase(t,0,.18)*(1.-phase(t,.89,t[-1]))
    arm(body,f,'r',gun[:,None]*np.array([-12,-8,-7])*sc,gun[:,None]*np.array([-7,0,-3])*sc,np.zeros((len(t),3)),t,gun)
    forward=phase(t,.09,.19)*(1.-phase(t,1.00,1.13))
    dualidle=np.array(d['clips']['Kukri.FullBody.Dual.Idle']['frames'][0])
    fingers(body,f,dualidle,'l',forward)
    f=finish(body,f,idle);f[0]=idle
    return f,t,forward,raw,palm,offset

def dual_pommel(body,d,idle):
    body.idle=idle.copy();src=d['clips']['Kukri.FullBody.Pommel'];t=clock(src['duration']);f=sample(src,t)
    w=phase(t,0,.18)*(1.-phase(t,t[-1]-.23,t[-1]));donor=f.copy()
    f=c.blend(np.repeat(idle[None],len(t),axis=0),f,(.35*w)[:,None,None])
    # The left blade stays in its own lane while the right pommel strikes.
    left=[i for i,n in enumerate(body.names) if n=='clavicle_l' or n.endswith('_l') and any(x in n for x in ('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
    f[:,left]=idle[left];sc=shoulder_scale(body)
    # Rebuild the main-hand arc on native shoulders. The old source travelled
    # too far in two frames around its preparation/cut boundary.
    ip,iq=body.world(idle);p,q=body.world(f);dp,dq=body.world(donor)
    ui,ei,hi=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    keys=[0,.17,.25,11/30,.44,.57,1.]
    reach=curve(t,keys,[(ip[hi]-ip[ui])/sc,[-12,17,20],[-12,23,31],[-3,43,-4],[-7,29,12],[-8,26,9],(ip[hi]-ip[ui])/sc])*sc
    pole=curve(t,keys,[(ip[ei]-ip[ui])/sc,[-23,3,4],[-25,6,8],[-20,16,-10],[-24,7,2],[-23,6,0],(ip[ei]-ip[ui])/sc])*sc
    desired=R.from_quat(c.slerp(np.broadcast_to(iq[hi],(len(t),4)),dq[:,hi],w[:,None]))
    solver.T=t;solver.solve_arm(body,f,'r',p[:,ui]+reach,p[:,ui]+pole,desired,w)
    g=curve(t,[0,.12,.25,.40,t[-1]],[0,.65,1,.6,0])
    arm(body,f,'l',g[:,None]*np.array([8,-4,-3])*sc,g[:,None]*np.array([5,-1,-3])*sc,g[:,None]*np.array([0,0,-.08]),t,g)
    fingers(body,f,idle,'r');fingers(body,f,idle,'l')
    return finish(body,f,idle),t

def dual_run(body,idle):
    body.idle=idle.copy();t=clock(.3);f=np.repeat(idle[None],len(t),axis=0);w=c.ease(t/t[-1]);sc=shoulder_scale(body)
    for side,vec,pole,roll in [('r',[-3,-12,-12],[-3,-5,-5],[.12,0,-.12]),('l',[3,-9,-8],[3,-4,-3],[.08,0,.10])]:
        arm(body,f,side,w[:,None]*vec*sc,w[:,None]*pole*sc,w[:,None]*roll,t,w)
    return finish(body,f,idle,end=False),t

def recover(body,d,idle,number):
    body.idle=idle.copy();src=d['clips'][f'Kukri.FullBody.Dual.Slash{number}'];end=np.array(src['frames'][-1]);t=clock(.5)
    f=c.blend(np.repeat(end[None],len(t),axis=0),np.repeat(idle[None],len(t),axis=0),phase(t,0,.5)[:,None,None])
    # Gentle residual recoil: zero position/velocity at both joins. The attack
    # already returns its hands, so a second broad swing would be incorrect.
    w=np.sin(np.pi*t/.5)**2*np.exp(-2*t/.5);sc=shoulder_scale(body)
    for side in 'rl':
        sign=1 if side=='l' else -1
        arm(body,f,side,w[:,None]*np.array([sign*1.2,-1.8,-1.4])*sc,w[:,None]*np.array([sign*.7,-.5,-.6])*sc,w[:,None]*np.array([.018,0,sign*.018]),t,w)
    f=finish(body,f,idle);f[0]=end
    return f,t

def main():
    data=json.loads((OUT/'inputs.json').read_text());report={'bodies':{},'runtime_tested':False};presentation={}
    for label,d in data.items():
        body=c.Body(old.base.rig.DATA[label]);assert body.names==d['names']
        idle=np.array(d['clips']['Kukri.FullBody.Idle']['frames'][0]);dual=np.array(d['clips']['Kukri.FullBody.Dual.Idle']['frames'][0]);clips={};presentation[label]={}
        def add(role,f,t,contact=.3,release=.6,source='Native authored completion',extra=None):
            clips[role]=dict(rate_num=RATE,rate_den=1,frames=f.tolist(),contact=contact,release=release,source=source,adaptation='Current native bone lengths, accepted hand grips and shared replicated action clock')
            if extra:clips[role].update(extra)
        for isdual,base,role in [(False,idle,'Kukri.FullBody.Equip'),(True,dual,'Kukri.FullBody.Dual.Equip')]:
            f,t,blades,events=equip(body,base,isdual);add(role,f,t,source='FPS Equip / DualEquip release and catch clock',extra=events)
            presentation[label]['DualEquip' if isdual else 'Equip']=dict(duration=float(t[-1]),blades=blades)
            print('AUTHORED',label,role,flush=True)
        f,t,forward,raw,palm,offset=offhand_uppercut(body,d)
        add('Pistol.KukriUppercut',f,t,.3/t[-1],.4333333/t[-1],d['clips']['Kukri.FullBody.Uppercut']['asset'])
        # Reverse mount is recorded in the accepted mixed-carry source.
        header=(ROOT/'Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredPose.h').read_text()
        import re
        match=re.search(r'KukriInHand=FTransform\(FQuat\(([^)]*)\),FVector\(([^)]*)\)',header)
        if not match:raise RuntimeError('Cannot read the accepted reverse-grip mount')
        parse=lambda s:np.array([float(x.strip().rstrip('f')) for x in s.split(',')])
        rq=R.from_quat(parse(match[1]));rp=parse(match[2]);bp=palm.apply(rp)+offset;bq=palm*rq
        mat=np.array(raw['kukri_in_hand']);fp=palm.apply(mat[:3,3])+offset;fq=palm*R.from_matrix(mat[:3,:3])
        mp=bp+(fp-bp)*forward[:,None];mq=R.from_quat(c.slerp(bq.as_quat(),fq.as_quat(),forward[:,None]))
        presentation[label]['Uppercut']=dict(duration=float(t[-1]),blades={'l':delta_mount(mp,mq,bp,bq).tolist()})
        print('AUTHORED',label,'Pistol.KukriUppercut',flush=True)
        f,t=dual_pommel(body,d,dual);add('Kukri.FullBody.Dual.Pommel',f,t,(11/30)/t[-1],.60/t[-1],source=d['clips']['Kukri.FullBody.Pommel']['asset'])
        f,t=dual_run(body,dual);add('Kukri.FullBody.Dual.Run',f,t)
        for number in (1,2):
            f,t=recover(body,d,dual,number);add(f'Kukri.FullBody.Dual.Recover{number}',f,t,source=d['clips'][f'Kukri.FullBody.Dual.Slash{number}']['asset'])
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=d['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        stats={}
        for role,clip in clips.items():
            a=np.array(clip['frames']);p,q=body.world(a)
            stats[role]=dict(frames=len(a),duration=(len(a)-1)/RATE,max_quat_error=float(abs(np.linalg.norm(a[:,:,3:7],axis=-1)-1).max()),max_scale_error=float(abs(a[:,:,7:]-body.ref[None,:,7:]).max()),hand_step_cm={s:float(np.linalg.norm(np.diff(p[:,body.ix['hand_'+s]],axis=0),axis=1).max()) for s in 'rl'})
        report['bodies'][label]=dict(previous_roles=d['previous_roles'],clips=stats)
        print('BODY_COMPLETE',label,len(clips),flush=True)
    (OUT/'presentation.json').write_text(json.dumps(presentation,separators=(',',':')))
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
