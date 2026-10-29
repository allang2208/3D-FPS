"""Single sprint chop V2: a visible overhead arc and momentum-braking support.

FPS supplies the raise/contact/release clock. The full-body wrist/blade path is
authored in shoulder space, rather than compressing the FPS camera crop.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
PREVIOUS=ROOT/'SourceAssets/KukriSingleDash20261028'
spec=importlib.util.spec_from_file_location('dash_v1',PREVIOUS/'author.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
base,c,arm,legs=old.base,old.c,old.arm,old.legs
INPUT=old.INPUT;FPS=old.FPS;TIMES=old.TIMES
RATE,LENGTH,CONTACT,RELEASE=old.RATE,old.LENGTH,old.CONTACT,old.RELEASE
phase,curve=old.phase,old.curve


def body_and_steps(body,captured):
    idle=np.asarray(captured['idle']);body.idle=idle.copy()
    f=np.repeat(idle[None],len(TIMES),axis=0)
    ip,iq=body.world(idle);size=body.scale/94.
    e=phase(0.,.17)*(1.-phase(.91,LENGTH))
    transfer=phase(.18,.41)*(1.-phase(.73,LENGTH))
    f[:,body.hip,0]+=3.*size*transfer
    f[:,body.hip,1]+=7.*size*transfer
    # Rise with the raised arm, then absorb the braking step through both knees.
    f[:,body.hip,2]+=curve([0.,.12,.25,.32,.42,.49,.62,.86,LENGTH],
        [0.,3.,5.,2.,-8.,-7.,-4.,-1.,0.])*size
    yaw=curve([0.,.17,.31,.39,.47,.65,.9,LENGTH],[0.,-13.,-14.,6.,10.,7.,2.,0.])
    pitch=curve([0.,.17,.31,.39,.46,.62,.9,LENGTH],[0.,7.,8.,-18.,-27.,-19.,-6.,0.])
    desired={}
    for name,amount in [('pelvis',0.),('spine_01',.18),('spine_02',.36),('spine_03',.57),('spine_04',.78),('spine_05',1.),('neck_01',.5),('neck_02',.3),('head',.15)]:
        if name not in body.ix:continue
        i=body.ix[name]
        rotation=R.from_euler('z',(yaw*(.4+.6*amount))[:,None],degrees=True)*R.from_euler('x',(pitch*amount)[:,None],degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(iq[i],rotation.as_quat(),e[:,None]))
        if name!='pelvis':f[:,i,:3]=idle[i,:3]+(body.ref[i,:3]-idle[i,:3])*e[:,None]
    body.set_world_rotations(f,desired)
    goals,rotations,headings={},{},{}
    for side,arrive,leave,angle in [('l',(.09,.32),(.98,1.30),-8.),('r',(.24,.49),(.76,1.035),12.)]:
        foot,ball=body.ix['foot_'+side],body.ix['ball_'+side]
        a,z=phase(*arrive),phase(*leave);w=a*(1.-z)
        bind=body.tp[ball]-body.tp[foot];bind_yaw=np.arctan2(-bind[0],bind[1])
        flat=R.from_euler('z',np.radians(angle)-bind_yaw)*R.from_quat(body.tq[foot])
        toe_local=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        end=ip[foot].copy();end[0]*=.70
        end[1]=ip[foot,1]+11.*size if side=='l' else -13.*size
        end+=flat.apply(toe_local);end[2]=ip[ball,2]
        toe=ip[ball]+(end-ip[ball])*w[:,None]
        # The lead foot folds back during lift, then reaches out to arrest the
        # actual CMC carry. The rear foot follows after push-off, never crosses.
        if side=='l':toe[:,1]-=18.*size*np.sin(np.pi*a)**2
        toe[:,2]+=((9. if side=='l' else 10.)*np.sin(np.pi*a)**2+5.*np.sin(np.pi*z)**2)*size
        q=R.from_quat(c.slerp(iq[foot],flat.as_quat(),w[:,None]))
        heel=phase(.08,.18)*(1.-phase(.24,.36))*np.radians(-15.) if side=='r' else -np.radians(10.)*np.sin(np.pi*a)**2
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
        limit=goals[side][:,2]+np.sqrt(np.maximum(1.,(.95*length)**2-xy))-(p[:,h,2]-p[:,body.hip,2])
        cap=np.minimum(cap,limit)
    drop=.35*np.logaddexp(0.,(f[:,body.hip,2]-cap)/.35)
    f[:,body.hip,2]-=gaussian_filter1d(drop,2.,mode='nearest')
    for side in 'lr':legs.hinge_leg(body,f,side,goals[side],rotations[side],headings[side],e)
    helper=f.copy();legs.lower.dual.leg_helpers(body,helper)
    seed=idle[None].copy();legs.lower.dual.leg_helpers(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('thigh_twist_','calf_twist_')):
            correction=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(correction*R.from_quat(helper[:,i,3:7])).as_quat()
    return f


def support_path(body,origin,goal,bend,desired,torso,head,weight,ip,iq):
    betas,banks=np.meshgrid(np.radians(np.arange(-100.,101.,10.)),np.radians(np.arange(-100.,101.,10.)),indexing='ij')
    choices=np.c_[betas.ravel(),banks.ravel()];count=len(choices)
    cost=np.empty((len(TIMES),count));wrist=R.from_quat(body.idle[body.ix['hand_r'],3:7])
    for k in range(len(TIMES)):
        origins=np.repeat(origin[k][None],count,axis=0);goals=np.repeat(goal[k][None],count,axis=0)
        bends=np.repeat(bend[k][None],count,axis=0)
        elbow,upper,fore=arm.solve_chain(body,origins,goals,bends,choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*desired[k]).magnitude()
        local=torso[k].inv().apply(elbow-origins)
        inward=np.maximum(0.,local[:,0]-1.)/10.
        clearance=np.zeros(count)
        for a,b in [(origins,elbow),(elbow,goals)]:
            for fract in (.3,.6,.9):
                distance=np.linalg.norm((a+(b-a)*fract-head[k])/[14.,15.,17.],axis=1)
                clearance+=np.maximum(0.,1.-distance)**2
        cost[k]=6.*residual**2+.10*choices[:,0]**2+.035*choices[:,1]**2+3.*inward**2+12.*clearance
    transition=.55*np.sum((choices[:,None]-choices[None])**2,axis=2)
    transition[np.max(np.abs(choices[:,None]-choices[None]),axis=2)>np.radians(10.1)]=np.inf
    back=np.zeros((len(TIMES),count),dtype=np.int32);score=cost[0].copy()
    for k in range(1,len(TIMES)):
        values=score[:,None]+transition;back[k]=np.argmin(values,axis=0)
        score=cost[k]+values[back[k],np.arange(count)]
    route=np.empty(len(TIMES),dtype=np.int32);route[-1]=int(np.argmin(score))
    for k in range(len(TIMES)-1,0,-1):route[k-1]=back[k,route[k]]
    return gaussian_filter1d(choices[route],.85,axis=0,mode='nearest')*weight[:,None]


def author_arms(body,f):
    ip,iq=body.world(body.idle);p,q=body.world(f);size=body.scale/94.
    chest=body.ix['spine_05'];torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    weight=phase(0.,.22)*(1.-phase(.82,LENGTH))
    raised=phase(.04,.18)*(1.-phase(.33,.45))
    clav=body.ix['clavicle_r']
    scapula=R.from_euler('y',(11.*raised)[:,None],degrees=True)*R.from_euler('z',(-7.*raised)[:,None],degrees=True)
    body.set_world_rotations(f,{clav:torso*scapula*idle_torso.inv()*R.from_quat(iq[clav])})
    p,q=body.world(f);ui,ei,hi=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    # Shoulder preparation leads the release at .27 s; the accelerated cut
    # crosses the existing .367-.467 s FPS contact window.
    theta=np.radians(curve([0.,.10,.19,.27,.31,.333,.367,.405,.46,.54,.68,.9,LENGTH],
        [-20.,55.,104.,112.,85.,65.,35.,0.,-43.,-46.,-43.,-25.,-20.]))
    radius=length*curve([0.,.18,.31,.367,.405,.46,.60,.9,LENGTH],[.83,.87,.88,.93,.95,.92,.86,.80,.83])
    x=length*curve([0.,.18,.31,.367,.405,.46,.65,.9,LENGTH],[-.2,-.22,-.23,-.20,-.13,-.04,-.03,-.2,-.2])
    local=np.c_[x,np.cos(theta)*radius,np.sin(theta)*radius]
    local0=idle_torso.inv().apply(ip[hi]-ip[ui])
    # Enter/leave along an arc as well. A Cartesian blend between a low idle
    # hand and an overhead hand collapses reach and makes the elbow snap open.
    seed=np.tile(c.unit(local0),(len(f),1));aim=c.align(seed,c.unit(local))
    direction=R.from_rotvec(aim.as_rotvec()*weight[:,None]).apply(seed)
    reach=np.linalg.norm(local0)+(np.linalg.norm(local,axis=1)-np.linalg.norm(local0))*weight
    local=direction*reach[:,None]
    norm=np.linalg.norm(local,axis=1);local*=np.minimum(1.,.955*length/np.maximum(norm,1e-8))[:,None]
    origin=p[:,ui];goal=origin+torso.apply(local)
    axis0=c.unit(torso.apply(np.tile(local0,(len(f),1))))
    bend0=torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(len(f),1)))
    bend0=c.unit(bend0-axis0*np.sum(bend0*axis0,axis=1)[:,None]);bend=c.align(axis0,c.unit(goal-origin)).apply(bend0)
    mount_pos,mount_rot=base.native.blade_mount(body)
    # Blade +Z is its tip axis; its broad face stays in the vertical cut plane.
    # Do not inherit the FPS blade's upward-pointing hidden recovery.
    blade_angle=np.radians(curve([0.,.10,.19,.27,.31,.333,.367,.405,.46,.54,.68,.9,LENGTH],
        [25.,100.,158.,167.,145.,120.,65.,12.,-35.,-42.,-37.,-10.,25.]))
    blade_axis=np.c_[np.full(len(f),-.06),np.cos(blade_angle),np.sin(blade_angle)]
    # c.frame maps its first input to +X. Build explicit +Z/+Y blade basis.
    z=c.unit(blade_axis);y=np.tile([-1.,0.,0.],(len(f),1));y=c.unit(y-z*np.sum(y*z,axis=1)[:,None]);x=c.unit(np.cross(y,z))
    blade_rotation=R.from_matrix(np.stack([x,y,z],axis=2))
    guided=torso*blade_rotation*mount_rot.inv()
    neutral=torso*idle_torso.inv()*R.from_quat(iq[hi])
    desired=R.from_quat(c.slerp(neutral.as_quat(),guided.as_quat(),weight[:,None]))
    head=p[:,body.ix['head']]+torso.apply(np.tile([0.,0.,7.],(len(f),1)))
    angles=support_path(body,origin,goal,bend,desired,torso,head,weight,ip,iq)
    elbow,upper,fore=arm.solve_chain(body,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    baseline=R.from_quat(body.idle[hi,3:7]);relative=(fore.inv()*desired*baseline.inv()).as_quat()
    axis=c.unit(body.ref[hi,:3]);twist=c.unit(np.c_[(relative[:,:3]@axis)[:,None]*axis,relative[:,3]])
    angle=np.unwrap(2.*np.arctan2(twist[:,:3]@axis,twist[:,3]));angle-=2.*np.pi*round(float(angle[0])/(2.*np.pi))
    limited_twist=R.from_rotvec(axis[None]*(np.radians(28.)*np.tanh(angle/np.radians(28.))*weight)[:,None])
    swing=R.from_quat(relative)*R.from_quat(twist).inv();v=swing.as_rotvec();a=np.linalg.norm(v,axis=1);limit=np.radians(32.)
    limited_swing=R.from_rotvec(v*(limit*np.tanh(a/limit)/np.maximum(a,1e-9)*weight)[:,None])
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:fore*limited_swing*limited_twist*baseline})
    # The free arm counterbalances the overhead load then opens behind/outside
    # the left hip during the chop; it never crosses the blade or the chest.
    p,_=body.world(f);ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    origin=p[:,ui];left0=idle_torso.inv().apply(ip[hi]-ip[ui])
    left=np.stack([curve([0.,.19,.31,.45,.65,.9,LENGTH],[14.,23.,24.,26.,22.,16.,14.]),
        curve([0.,.19,.31,.45,.65,.9,LENGTH],[12.,23.,23.,-9.,-11.,8.,12.]),
        curve([0.,.19,.31,.45,.65,.9,LENGTH],[-22.,-12.,-11.,-23.,-24.,-24.,-22.])],axis=1)*size
    left=left0+(left-left0)*weight[:,None];goal=origin+torso.apply(left)
    axis0=c.unit(torso.apply(np.tile(left0,(len(f),1))))
    reach=c.unit(goal-origin)
    seed=torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(len(f),1)))
    seed=c.unit(seed-axis0*np.sum(seed*axis0,axis=1)[:,None])
    # Transport the native flexion plane; a linear elbow pole crosses the
    # reach axis during the backward counter-swing and flips the shoulder.
    pole=origin+c.align(axis0,reach).apply(seed)*30.*size
    _,fore=legs.lower.dual.limb(body,f,'l',('upperarm','lowerarm','hand'),goal,pole)
    body.set_world_rotations(f,{hi:fore*R.from_quat(body.idle[hi,3:7])})
    relax=.18*phase(.06,.19)*(1.-phase(.65,LENGTH))
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.split('_')[0] in ('index','middle','ring','pinky'):
            f[:,i,3:7]=c.slerp(body.idle[i,3:7],body.ref[i,3:7],relax[:,None])
    helpers=f.copy();base.native.native_twists(body,helpers)
    seed=body.idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(body.idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(offset*R.from_quat(helpers[:,i,3:7])).as_quat()
    return dict(elbow_plane_degrees=np.degrees(angles[:,0]).tolist(),forearm_bank_degrees=np.degrees(angles[:,1]).tolist())


def diagnose(body,f):
    """User-requested scoped source-pose review; not an in-game acceptance."""
    p,q=body.world(f);h,u,e=[body.ix[n+'_r'] for n in ('hand','upperarm','lowerarm')]
    mp,mr=base.native.blade_mount(body);hand=R.from_quat(q[:,h]);blade=hand*mr
    axis=blade.apply(np.tile([0.,0.,1.],(len(f),1)))
    tip=p[:,h]+hand.apply(mp)+blade.apply(np.tile([6.179,0.,26.291],(len(f),1)))
    chest=body.ix['spine_05'];torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    relative=torso.inv().apply(p[:,h]-p[:,u]);elevation=np.degrees(np.arctan2(relative[:,2],relative[:,1]))
    flex=np.degrees(np.arccos(np.clip(np.sum(c.unit(p[:,e]-p[:,u])*c.unit(p[:,h]-p[:,e]),axis=1),-1.,1.)))
    rows=[]
    for t in [.19,.31,.367,.405,.46,.54,.68]:
        k=round(t*RATE)
        rows.append(dict(seconds=t,wrist_cm=p[k,h].tolist(),blade_tip_cm=tip[k].tolist(),blade_tip_direction=axis[k].tolist(),
            arm_elevation_degrees=float(elevation[k]),elbow_flex_degrees=float(flex[k]),pelvis_z_cm=float(p[k,body.hip,2])))
    cut=(TIMES>=.30)&(TIMES<=.55)
    return dict(keyframes=rows,wrist_chop_vertical_span_cm=float(np.ptp(p[cut,h,2])),
        tip_chop_vertical_span_cm=float(np.ptp(tip[cut,2])),legs=legs.diagnose(body,f),runtime_tested=False)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    saved=json.loads((PREVIOUS/'assets-saved.json').read_text())
    report=dict(version='Single sprint overhead impact V2',source=FPS['dash']['asset'],seconds=LENGTH,rate=RATE,
        contact_seconds=CONTACT,release_seconds=RELEASE,bodies={},first_person_changed=False,runtime_tested=False,rendered=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label];captured=INPUT['targets'][label]
        previous=saved['bodies'][label]['clips']['Kukri.FullBody.Dash']
        if active['clips']['Kukri.FullBody.Dash']!=previous or active['clips']['Kukri.FullBody.Idle']!=captured['idle_asset'] or active['body_mesh']!=data['mesh']:
            raise RuntimeError('Captured body boundary changed: '+label)
        old_bytes=(PREVIOUS/(label+'-actions.json')).read_bytes()
        if hashlib.sha256(old_bytes).hexdigest()!=saved['bodies'][label]['source_sha256']:raise RuntimeError('Previous source no longer matches saved asset')
        before=np.asarray(json.loads(old_bytes)['clips']['Dash']['frames'])
        body=c.Body(data);body.idle=before[0].copy();before_review=diagnose(body,before)
        frames=body_and_steps(body,captured);detail=author_arms(body,frames)
        frames[0]=body.idle;frames[-1]=body.idle
        for k in range(1,len(frames)):
            frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
        review=diagnose(body,frames)
        clip=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=CONTACT/LENGTH,release=RELEASE/LENGTH,
            source=FPS['dash']['asset'],adaptation='Full shoulder-driven overhead arc, downward blade follow-through, lead braking step and rear catch step; same FPS timing and native grip; no capsule or camera changes')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Dash':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={'Dash':previous},source_idle=captured['idle_asset'],
            frames=len(frames),before=before_review,after=review,**detail)
        print(label,json.dumps(dict(before_wrist_span=before_review['wrist_chop_vertical_span_cm'],after_wrist_span=review['wrist_chop_vertical_span_cm'],keys=review['keyframes'])),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
