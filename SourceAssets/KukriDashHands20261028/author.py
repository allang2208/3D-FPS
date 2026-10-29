"""Natural single offhand and dedicated dual-blade overhead sprint chop.

Reuse the saved V2 main arm and support take. All left-arm poses are solved
against the native left hinge and the actual single/dual carry boundary.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
dash=module('dash_impact','SourceAssets/KukriSingleDashImpact20261028/author.py')
carry=module('dash_dual_carry','SourceAssets/KukriDualIdleThirdPerson20261027/author.py')
base,c=dash.base,dash.c
TIMES=dash.TIMES;RATE=dash.RATE;LENGTH=dash.LENGTH
phase,curve=dash.phase,dash.curve


def left_helpers(body,f,idle):
    derived=f.copy();base.native.native_twists(body,derived)
    seed=idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(offset*R.from_quat(derived[:,i,3:7])).as_quat()


def solve_left(body,origin,goal,bend,beta,bank,ip,iq):
    ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    u0,v0=ip[ei]-ip[ui],ip[hi]-ip[ei]
    l1,l2=np.linalg.norm(u0),np.linalg.norm(v0)
    axis=c.unit(goal-origin);d=np.linalg.norm(goal-origin,axis=-1)
    along=(l1*l1-l2*l2+d*d)/(2.*d)
    bend=R.from_rotvec(axis*beta[...,None]).apply(bend)
    elbow=origin+axis*along[...,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[...,None]
    u,v=elbow-origin,goal-elbow
    uq=c.frame(u,v)*c.frame(u0,v0).inv()*R.from_quat(iq[ui])
    fq=R.from_rotvec(c.unit(v)*bank[...,None])*c.frame(v,u)*c.frame(v0,u0).inv()*R.from_quat(iq[ei])
    return elbow,uq,fq


def transported_bend(torso,idle_torso,ip,ui,ei,hi,axis):
    native_axis=c.unit(torso.apply(np.tile(idle_torso.inv().apply(ip[hi]-ip[ui]),(len(TIMES),1))))
    seed=torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(len(TIMES),1)))
    seed=c.unit(seed-native_axis*np.sum(seed*native_axis,axis=1)[:,None])
    return c.align(native_axis,axis).apply(seed)


def single_free_arm(body,original):
    f=original.copy();idle=original[0].copy();body.idle=idle
    for i,name in enumerate(body.names):
        if carry.left_bone(name):f[:,i]=idle[i]
    ip,iq=body.world(idle);p,q=body.world(f);size=body.scale/94.
    chest=body.ix['spine_05'];ci=body.ix['clavicle_l']
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    w=phase(0.,.21)*(1.-phase(.86,LENGTH))
    # Small scapular counter-swing. The free elbow hangs near the side, rather
    # than holding the previous wide, chest-height balancing pose.
    sweep=curve([0.,.19,.30,.48,.67,.92,LENGTH],[0.,-3.,-3.,4.,3.,1.,0.])*w
    body.set_world_rotations(f,{ci:torso*R.from_euler('z',sweep[:,None],degrees=True)*idle_torso.inv()*R.from_quat(iq[ci])})
    p,_=body.world(f);ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    origin=p[:,ui];local0=idle_torso.inv().apply(ip[hi]-ip[ui])
    keys=[0.,.19,.30,.39,.49,.65,.84,1.03,LENGTH]
    # The shoulder leads, elbow follows, and hand settles a little later.
    local=np.stack([curve(keys,[9.,10.,11.,11.,9.,9.,10.,10.,9.]),
        curve(keys,[8.,20.,21.,13.,-7.,-10.,-2.,7.,8.]),
        curve(keys,[-33.,-27.,-26.,-31.,-36.,-37.,-35.,-33.,-33.])],axis=1)*size
    local=local0+(local-local0)*w[:,None]
    goal=origin+torso.apply(local);axis=c.unit(goal-origin)
    seed=transported_bend(torso,idle_torso,ip,ui,ei,hi,axis)
    desired=torso.apply(np.tile([14.,1.,-25.],(len(f),1))*size)
    desired=c.unit(desired-axis*np.sum(desired*axis,axis=1)[:,None])
    roll=np.unwrap(np.arctan2(np.sum(axis*np.cross(seed,desired),axis=1),np.sum(seed*desired,axis=1)))
    bend=R.from_rotvec(axis*(roll*w)[:,None]).apply(seed)
    bank=np.radians(curve(keys,[0.,-5.,-4.,0.,5.,7.,4.,0.,0.]))*w
    _,upper,fore=solve_left(body,origin,goal,bend,np.zeros(len(f)),bank,ip,iq)
    # Low-amplitude wrist follow-through, on the native wrist flexion axes.
    wrist=R.from_euler('yz',np.c_[curve(keys,[0.,-2.,-2.,0.,3.,4.,1.,0.,0.]),
        curve(keys,[0.,2.,3.,2.,-2.,-3.,-1.,0.,0.])]*w[:,None],degrees=True)
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:fore*R.from_quat(idle[hi,3:7])*wrist})
    relax=.22*phase(.05,.25)*(1.-phase(.76,LENGTH))
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.split('_')[0] in ('index','middle','ring','pinky'):
            f[:,i,3:7]=c.slerp(idle[i,3:7],body.ref[i,3:7],relax[:,None])
    left_helpers(body,f,idle);f[0]=original[0];f[-1]=original[-1]
    return f


def dual_support(body,origin,goal,bend,desired,torso,head,weight,ip,iq):
    beta,bank=np.meshgrid(np.radians(np.arange(-50.,51.,10.)),np.radians(np.arange(-100.,101.,10.)),indexing='ij')
    choices=np.c_[beta.ravel(),bank.ravel()];count=len(choices);n=len(TIMES)
    cost=np.empty((n,count));wrist=R.from_quat(body.idle[body.ix['hand_l'],3:7])
    for k in range(n):
        a=np.repeat(origin[k][None],count,axis=0);g=np.repeat(goal[k][None],count,axis=0);b=np.repeat(bend[k][None],count,axis=0)
        elbow,upper,fore=solve_left(body,a,g,b,choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*desired[k]).magnitude()
        elbow_local=torso[k].inv().apply(elbow-a)
        inward=np.maximum(0.,-elbow_local[:,0]-1.)/10.
        clearance=np.zeros(count)
        for start,end in [(a,elbow),(elbow,g)]:
            for fract in (.3,.6,.9):
                distance=np.linalg.norm((start+(end-start)*fract-head[k])/[14.,15.,17.],axis=1)
                clearance+=np.maximum(0.,1.-distance)**2
        cost[k]=6.*residual**2+.18*choices[:,0]**2+.04*choices[:,1]**2+3.*inward**2+12.*clearance
    difference=choices[:,None]-choices[None]
    transition=.55*np.sum(difference*difference,axis=2)
    transition[np.max(np.abs(difference),axis=2)>np.radians(10.1)]=np.inf
    back=np.zeros((n,count),dtype=np.int32);score=cost[0].copy()
    for k in range(1,n):
        values=score[:,None]+transition;back[k]=np.argmin(values,axis=0)
        score=cost[k]+values[back[k],np.arange(count)]
    route=np.empty(n,dtype=np.int32);route[-1]=int(np.argmin(score))
    for k in range(n-1,0,-1):route[k-1]=back[k,route[k]]
    return gaussian_filter1d(choices[route],1.,axis=0,mode='nearest')*weight[:,None]


def dual_overhead(body,original,idle):
    f=original.copy();body.idle=idle.copy();n=len(f)
    # Preserve the saved main-arm chop and shared support. Only the matching
    # dual carry is used at the clip boundaries.
    boundary=phase(0.,.12)*(1.-phase(.97,LENGTH))
    f=c.blend(np.repeat(idle[None],n,axis=0),f,boundary[:,None,None])
    for i,name in enumerate(body.names):
        if carry.left_bone(name):f[:,i]=idle[i]
    ip,iq=body.world(idle);p,q=body.world(f)
    chest=body.ix['spine_05'];ci=body.ix['clavicle_l']
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    weight=phase(0.,.22)*(1.-phase(.82,LENGTH))
    raised=phase(.04,.18)*(1.-phase(.33,.45))
    scapula=R.from_euler('y',(-11.*raised)[:,None],degrees=True)*R.from_euler('z',(7.*raised)[:,None],degrees=True)
    body.set_world_rotations(f,{ci:torso*scapula*idle_torso.inv()*R.from_quat(iq[ci])})
    p,q=body.world(f)
    ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    ur,er,hr=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(ip[ei]-ip[ui])+np.linalg.norm(ip[hi]-ip[ei])
    right_length=np.linalg.norm(ip[er]-ip[ur])+np.linalg.norm(ip[hr]-ip[er])
    mirror=np.array([-1.,1.,1.]);origin=p[:,ui]
    # Mirror geometric reach in chest space, never native left/right quats.
    local=torso.inv().apply(p[:,hr]-p[:,ur])*mirror*length/right_length
    local[:,0]+=.035*length*weight
    local0=idle_torso.inv().apply(ip[hi]-ip[ui])
    seed_axis=np.tile(c.unit(local0),(n,1));turn=c.align(seed_axis,c.unit(local))
    direction=R.from_rotvec(turn.as_rotvec()*weight[:,None]).apply(seed_axis)
    radius=np.linalg.norm(local0)+(np.linalg.norm(local,axis=1)-np.linalg.norm(local0))*weight
    goal=origin+torso.apply(direction*np.minimum(radius,.955*length)[:,None])
    axis=c.unit(goal-origin);seed=transported_bend(torso,idle_torso,ip,ui,ei,hi,axis)
    mirrored_elbow=torso.apply(torso.inv().apply(p[:,er]-p[:,ur])*mirror)
    wanted=c.unit(mirrored_elbow-axis*np.sum(mirrored_elbow*axis,axis=1)[:,None])
    roll=np.unwrap(np.arctan2(np.sum(axis*np.cross(seed,wanted),axis=1),np.sum(seed*wanted,axis=1)))
    bend=R.from_rotvec(axis*(roll*weight)[:,None]).apply(seed)
    _,_,left_mount=carry.dual.v1.left_grip(body)
    _,right_mount=base.native.blade_mount(body)
    right_blade=(torso.inv()*R.from_quat(q[:,hr])*right_mount).as_matrix()
    mirrored=np.diag(mirror)[None]@right_blade@np.diag([1.,-1.,1.])[None]
    guided=torso*R.from_matrix(mirrored)*left_mount.inv()
    neutral=torso*idle_torso.inv()*R.from_quat(iq[hi])
    desired=R.from_quat(c.slerp(neutral.as_quat(),guided.as_quat(),weight[:,None]))
    head=p[:,body.ix['head']]+torso.apply(np.tile([0.,0.,7.],(n,1)))
    angles=dual_support(body,origin,goal,bend,desired,torso,head,weight,ip,iq)
    _,upper,fore=solve_left(body,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    baseline=R.from_quat(idle[hi,3:7]);relative=(fore.inv()*desired*baseline.inv()).as_quat()
    longitudinal=c.unit(body.ref[hi,:3])
    twist=c.unit(np.c_[(relative[:,:3]@longitudinal)[:,None]*longitudinal,relative[:,3]])
    angle=np.unwrap(2.*np.arctan2(twist[:,:3]@longitudinal,twist[:,3]));angle-=2.*np.pi*round(float(angle[0])/(2.*np.pi))
    limited_twist=R.from_rotvec(longitudinal[None]*(np.radians(28.)*np.tanh(angle/np.radians(28.))*weight)[:,None])
    swing=(R.from_quat(relative)*R.from_quat(twist).inv()).as_rotvec();amount=np.linalg.norm(swing,axis=1);limit=np.radians(32.)
    limited_swing=R.from_rotvec(swing*(limit*np.tanh(amount/limit)/np.maximum(amount,1e-9)*weight)[:,None])
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:fore*limited_swing*limited_twist*baseline})
    # Both blades keep their own native finger contact for the whole motion.
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=idle[i]
    left_helpers(body,f,idle);f[0]=idle;f[-1]=idle
    return f,dict(elbow_plane_degrees=np.degrees(angles[:,0]).tolist(),forearm_bank_degrees=np.degrees(angles[:,1]).tolist())


def saved_source(folder,label,role,active,data):
    receipt=json.loads((folder/'assets-saved.json').read_text())['bodies'][label]
    raw=(folder/(label+'-actions.json')).read_bytes();source=json.loads(raw)
    asset=receipt['clips']['Kukri.FullBody.'+role]
    if hashlib.sha256(raw).hexdigest()!=receipt['source_sha256'] or active['clips']['Kukri.FullBody.'+role]!=asset:
        raise RuntimeError('Saved source changed: '+label+' '+role)
    if source['names']!=data['names'] or source['mesh']!=active['body_mesh']:raise RuntimeError('Native source mismatch')
    return source['clips'][role],asset


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Single natural free arm V3 / dual overhead V1',bodies={},runtime_tested=False,rendered=False,first_person_changed=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        source,asset=saved_source(ROOT/'SourceAssets/KukriSingleDashImpact20261028',label,'Dash',active,data)
        idle,carry_asset=saved_source(ROOT/'SourceAssets/KukriDualIdleThirdPerson20261027',label,'Dual.Idle',active,data)
        original=np.asarray(source['frames']);body=c.Body(data)
        single=single_free_arm(body,original)
        dual,detail=dual_overhead(body,original,np.asarray(idle['frames'][0]))
        clips={}
        for role,frames,adaptation in [('Dash',single,'Saved overhead chop/support; close natural left counter-swing with shoulder-elbow-wrist follow-through'),
            ('Dual.Dash',dual,'Dedicated simultaneous dual-blade overhead chop; native left hinge and fixed dual grip; matched dual carry and braking support')]:
            for k in range(1,len(frames)):
                frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
            clips[role]=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=source['contact'],release=source['release'],source=asset,adaptation=adaptation)
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(previous_roles={'Dash':asset,'Dual.Dash':active['clips'].get('Kukri.FullBody.Dual.Dash')},
            source_idle=carry_asset,source_single=asset,frames=len(original),**detail)
        print('DASH_HANDS_AUTHORED',label,'Dash, Dual.Dash',flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
