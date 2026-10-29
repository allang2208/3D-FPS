"""Native single-blade sprint raise / overhead chop, on the installed FPS clock."""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


arm=module('dash_native_arm','SourceAssets/KukriSingleUppercutArm20261027/author.py')
legs=module('dash_native_legs','SourceAssets/KukriSingleUppercutLegs20261027/author.py')
base,c=arm.base,arm.c
INPUT=json.loads((OUT/'inputs.json').read_text())
FPS=INPUT['native'];SI={name:i for i,name in enumerate(FPS['names'])}
RATE=120;LENGTH=40./30.;CONTACT=.367;RELEASE=.467
TIMES=np.arange(round(LENGTH*RATE)+1)/RATE
C=R.from_euler('z',180.,degrees=True)


def phase(a,b):return base.smooth((TIMES-a)/(b-a))


def curve(times,values):return PchipInterpolator(times,values)(TIMES)


def support_path(body,origin,goal,bend,desired,torso,head,weight,ip,iq):
    """Allocate the blade turn to a continuous elbow plane and forearm bank."""
    betas,banks=np.meshgrid(np.radians(np.arange(-80.,81.,10.)),np.radians(np.arange(-100.,101.,10.)),indexing='ij')
    choices=np.c_[betas.ravel(),banks.ravel()]
    count=len(choices);cost=np.empty((len(TIMES),count))
    wrist=R.from_quat(body.idle[body.ix['hand_r'],3:7])
    for k in range(len(TIMES)):
        origins=np.repeat(origin[k][None],count,axis=0)
        goals=np.repeat(goal[k][None],count,axis=0)
        bends=np.repeat(bend[k][None],count,axis=0)
        elbow,upper,fore=arm.solve_chain(body,origins,goals,bends,choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*desired[k]).magnitude()
        local=torso[k].inv().apply(elbow-origins)
        inward=np.maximum(0.,local[:,0]-5.)/10.
        clearance=np.zeros(count)
        for a,b in [(origins,elbow),(elbow,goals)]:
            for f in (.3,.6,.9):
                distance=np.linalg.norm((a+(b-a)*f-head[k])/[14.,15.,17.],axis=1)
                clearance+=np.maximum(0.,1.-distance)**2
        cost[k]=residual**2+.12*choices[:,0]**2+.035*choices[:,1]**2+2.*inward**2+8.*clearance
    transition=3.*np.sum((choices[:,None]-choices[None])**2,axis=2)
    back=np.zeros((len(TIMES),count),dtype=np.int32);score=cost[0].copy()
    for k in range(1,len(TIMES)):
        values=score[:,None]+transition;back[k]=np.argmin(values,axis=0)
        score=cost[k]+values[back[k],np.arange(count)]
    route=np.empty(len(TIMES),dtype=np.int32);route[-1]=int(np.argmin(score))
    for k in range(len(TIMES)-1,0,-1):route[k-1]=back[k,route[k]]
    return gaussian_filter1d(choices[route],1.6,axis=0,mode='nearest')*weight[:,None]


def body_and_steps(body,captured):
    idle=np.asarray(captured['idle']);body.idle=idle.copy()
    f=np.repeat(idle[None],len(TIMES),axis=0)
    ip,iq=body.world(idle);size=body.scale/94.
    e=phase(0.,.16)*(1.-phase(.92,LENGTH))
    donor=captured['sword_dash']
    clock=PchipInterpolator([0.,.13,.333,CONTACT,RELEASE,LENGTH],
        [0.,.15,.25,donor['markers']['Contact'],donor['markers']['Release'],donor['duration']])(TIMES)
    take=np.array([c.sample(np.asarray(donor['frames']),float(t),donor['rate']) for t in clock]);take[:,0]=idle[0]
    dp,_=body.world(take)
    lift=np.clip(gaussian_filter1d(dp[:,body.hip,2]-dp[0,body.hip,2],3.,mode='nearest'),-8.*size,6.*size)
    f[:,body.hip,2]+=.65*lift*e
    advance=phase(.14,.40)*(1.-phase(.72,LENGTH))
    f[:,body.hip,0]+=2.*size*advance
    f[:,body.hip,1]+=4.*size*advance
    yaw=curve([0.,.13,.30,.43,.60,.9,LENGTH],[0.,-6.,-6.,5.,5.,2.,0.])
    pitch=curve([0.,.13,.30,.43,.60,.9,LENGTH],[0.,-5.,-5.,-13.,-10.,-5.,0.])
    desired={}
    for name,amount in [('pelvis',0.),('spine_01',.18),('spine_02',.36),('spine_03',.57),('spine_04',.78),('spine_05',1.),('neck_01',.5),('neck_02',.3),('head',.2)]:
        if name not in body.ix:continue
        i=body.ix[name]
        rotation=R.from_euler('z',(yaw*(.4+.6*amount))[:,None],degrees=True)*R.from_euler('x',(pitch*amount)[:,None],degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(iq[i],rotation.as_quat(),e[:,None]))
        if name!='pelvis':f[:,i,:3]=idle[i,:3]+(body.ref[i,:3]-idle[i,:3])*e[:,None]
    body.set_world_rotations(f,desired)
    goals,rotations,headings={},{},{}
    for side,arrive,leave,angle in [('l',(.09,.345),(.975,1.31),-9.),('r',(.22,.51),(.73,1.035),15.)]:
        foot,ball=body.ix['foot_'+side],body.ix['ball_'+side]
        a,z=phase(*arrive),phase(*leave);w=a*(1.-z)
        bind=body.tp[ball]-body.tp[foot];bind_yaw=np.arctan2(-bind[0],bind[1])
        flat=R.from_euler('z',np.radians(angle)-bind_yaw)*R.from_quat(body.tq[foot])
        toe_local=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        end=ip[foot].copy();end[0]*=.85;end[1]=ip[foot,1]+9.*size if side=='l' else -18.*size
        end+=flat.apply(toe_local);end[2]=ip[ball,2]
        toe=ip[ball]+(end-ip[ball])*w[:,None]
        toe[:,2]+=(6.*np.sin(np.pi*a)**2+4.5*np.sin(np.pi*z)**2)*size
        q=R.from_quat(c.slerp(iq[foot],flat.as_quat(),w[:,None]))
        if side=='r':
            heel=phase(.10,.22)*(1.-phase(.23,.38))*np.radians(-10.)
            direction=q.apply(np.tile(toe_local,(len(f),1)))
            lateral=c.unit(np.c_[direction[:,1],-direction[:,0],np.zeros(len(f))])
            q=R.from_rotvec(lateral*heel[:,None])*q
        goals[side]=toe-q.apply(np.tile(toe_local,(len(f),1)))
        rotations[side]=q;direction=q.apply(np.tile(toe_local,(len(f),1)))
        headings[side]=np.arctan2(-direction[:,0],direction[:,1])
    p,_=body.world(f);cap=np.full(len(f),np.inf)
    for side in 'lr':
        h,k,a=[body.ix[n+'_'+side] for n in ('thigh','calf','foot')]
        length=np.linalg.norm(ip[k]-ip[h])+np.linalg.norm(ip[a]-ip[k])
        xy=np.sum((goals[side][:,:2]-p[:,h,:2])**2,axis=1)
        limit=goals[side][:,2]+np.sqrt(np.maximum(1.,(.958*length)**2-xy))-(p[:,h,2]-p[:,body.hip,2])
        cap=np.minimum(cap,limit)
    drop=.35*np.logaddexp(0.,(f[:,body.hip,2]-cap)/.35)
    f[:,body.hip,2]-=gaussian_filter1d(drop,2.5,mode='nearest')
    for side in 'lr':legs.hinge_leg(body,f,side,goals[side],rotations[side],headings[side],e)
    helper=f.copy();legs.lower.dual.leg_helpers(body,helper)
    seed=idle[None].copy();legs.lower.dual.leg_helpers(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('thigh_twist_','calf_twist_')):
            correction=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(correction*R.from_quat(helper[:,i,3:7])).as_quat()
    return f,clock


def author_arms(body,f):
    ip,iq=body.world(body.idle);p,q=body.world(f)
    chest=body.ix['spine_05'];torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    weight=phase(0.,.12)*(1.-phase(.88,LENGTH))
    raised=phase(.05,.14)*(1.-phase(.333,.43))
    i=body.ix['clavicle_r']
    scapula=R.from_euler('y',(7.*raised)[:,None],degrees=True)*R.from_euler('z',(-4.*raised)[:,None],degrees=True)
    body.set_world_rotations(f,{i:torso*scapula*idle_torso.inv()*R.from_quat(iq[i])})
    p,q=body.world(f);ui,ei,hi=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    source=np.asarray(FPS['dash']['frames'])
    su,se,sh=[SI[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    source_length=np.mean(np.linalg.norm(source[:,se,:3]-source[:,su,:3],axis=1)+np.linalg.norm(source[:,sh,:3]-source[:,se,:3],axis=1))
    motion=np.array([c.sample(source,float(t),FPS['dash']['rate']) for t in TIMES])
    hand=C.apply(motion[:,sh,:3]-motion[:,su,:3])*length/source_length
    local=np.c_[.55*hand[:,0]-.15*length,.65*hand[:,1]+.18*length,.94*hand[:,2]+.02*length]
    local0=idle_torso.inv().apply(ip[hi]-ip[ui])
    local=local0+(local-local0)*weight[:,None]
    # Keep the working arc extended in front of the chest during the chop.
    norm=np.linalg.norm(local,axis=1)
    stroke=phase(.315,.355)*(1.-phase(.46,.55))
    radius=norm+np.maximum(0.,.70*length-norm)*stroke
    local*=np.minimum(radius,.94*length)[:,None]/np.maximum(norm[:,None],1e-8)
    origin=p[:,ui];goal=origin+torso.apply(local)
    axis0=c.unit(torso.apply(np.tile(local0,(len(f),1))))
    bend0=torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(len(f),1)))
    bend0=c.unit(bend0-axis0*np.sum(bend0*axis0,axis=1)[:,None])
    bend=c.align(axis0,c.unit(goal-origin)).apply(bend0)
    mount,_=base.native.palm_mount(body,'r')
    # The hidden FPS recovery rolls its wrist for the camera. Keep the visible
    # third-person follow-through in the cut's supported palm, then recover.
    rotation_source=np.array([c.sample(source,float(min(t,.433)),FPS['dash']['rate']) for t in TIMES])
    source_hand=torso*C*R.from_quat(rotation_source[:,sh,3:7])*mount.inv()
    neutral_hand=torso*idle_torso.inv()*R.from_quat(iq[hi])
    hand_weight=phase(0.,.12)*(1.-phase(.70,LENGTH))
    desired=R.from_quat(c.slerp(neutral_hand.as_quat(),source_hand.as_quat(),hand_weight[:,None]))
    head=p[:,body.ix['head']]+torso.apply(np.tile([0.,0.,6.],(len(f),1)))
    angles=support_path(body,origin,goal,bend,desired,torso,head,weight,ip,iq)
    elbow,upper,fore=arm.solve_chain(body,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    baseline=R.from_quat(body.idle[hi,3:7]);relative=(fore.inv()*desired*baseline.inv()).as_quat()
    axis=c.unit(body.ref[hi,:3]);twist=c.unit(np.c_[(relative[:,:3]@axis)[:,None]*axis,relative[:,3]])
    angle=np.unwrap(2.*np.arctan2(twist[:,:3]@axis,twist[:,3]));angle-=2.*np.pi*round(float(angle[0])/(2.*np.pi))
    limited_twist=R.from_rotvec(axis[None]*(np.radians(25.)*np.tanh(angle/np.radians(25.))*weight)[:,None])
    swing=R.from_quat(relative)*R.from_quat(twist).inv();v=swing.as_rotvec();a=np.linalg.norm(v,axis=1);limit=np.radians(20.)
    limited_swing=R.from_rotvec(v*(limit*np.tanh(a/limit)/np.maximum(a,1e-9)*weight)[:,None])
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:fore*limited_swing*limited_twist*baseline})

    # Free left arm balances the overhead load and landing. It stays outside
    # the torso and does not acquire a second weapon or a false hilt contact.
    p,_=body.world(f);ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    size=body.scale/94.;origin=p[:,ui]
    left0=idle_torso.inv().apply(ip[hi]-ip[ui])
    left=np.stack([curve([0.,.16,.32,.43,.65,LENGTH],[10.,13.,13.,10.,8.,10.]),
        curve([0.,.16,.32,.43,.65,LENGTH],[15.,10.,10.,22.,18.,15.]),
        curve([0.,.16,.32,.43,.65,LENGTH],[-20.,-17.,-17.,-22.,-25.,-20.])],axis=1)*size
    left=left0+(left-left0)*weight[:,None]
    goal=origin+torso.apply(left)
    pole=origin+torso.apply(np.tile([23.,2.,-17.],(len(f),1))*size)
    idle_pole=origin+torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(len(f),1)))
    pole=idle_pole+(pole-idle_pole)*weight[:,None]
    _,fore=legs.lower.dual.limb(body,f,'l',('upperarm','lowerarm','hand'),goal,pole)
    body.set_world_rotations(f,{hi:fore*R.from_quat(body.idle[hi,3:7])})
    relax=.14*phase(.07,.22)*(1.-phase(.65,LENGTH))
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.split('_')[0] in ('index','middle','ring','pinky'):
            f[:,i,3:7]=c.slerp(body.idle[i,3:7],body.ref[i,3:7],relax[:,None])
    helpers=f.copy();base.native.native_twists(body,helpers)
    seed=body.idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(body.idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(offset*R.from_quat(helpers[:,i,3:7])).as_quat()
    return dict(elbow_plane_degrees=np.degrees(angles[:,0]).tolist(),forearm_bank_degrees=np.degrees(angles[:,1]).tolist(),
        wrist_swing_soft_limit_degrees=20,wrist_twist_soft_limit_degrees=25)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Single sprint overhead V1',source=FPS['dash']['asset'],seconds=LENGTH,rate=RATE,
        contact_seconds=CONTACT,release_seconds=RELEASE,bodies={},first_person_changed=False,runtime_tested=False,rendered=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label];captured=INPUT['targets'][label]
        if active['clips']['Kukri.FullBody.Dash']!=captured['previous']['asset'] or active['clips']['Kukri.FullBody.Idle']!=captured['idle_asset'] or active['body_mesh']!=data['mesh']:
            raise RuntimeError('Captured dash or body boundary changed: '+label)
        if data['names']!=captured['names']:raise RuntimeError('Native track order mismatch')
        body=c.Body(data);frames,clock=body_and_steps(body,captured);detail=author_arms(body,frames)
        frames[0]=body.idle;frames[-1]=body.idle
        for k in range(1,len(frames)):
            frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
        clip=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=CONTACT/LENGTH,release=RELEASE/LENGTH,
            source=FPS['dash']['asset'],adaptation='FPS-timed single-blade overhead raise and chop; native arm hinge/forearm support, free left balance, supported leading-foot plant and recovery; no camera motion copied')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Dash':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={'Dash':captured['previous']['asset']},
            source_idle=captured['idle_asset'],source_body=captured['sword_dash']['asset'],body_source_clock=clock.tolist(),frames=len(frames),**detail)
        print('SINGLE_DASH_AUTHORED',label,len(frames),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
