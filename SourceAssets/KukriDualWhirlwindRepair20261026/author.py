"""V2: supported squat, open knees, anatomical arms and free blade banking."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
s=importlib.util.spec_from_file_location('dual_grip_v1',ROOT/'SourceAssets/KukriDualWhirlwind20261026/author.py')
v1=importlib.util.module_from_spec(s);s.loader.exec_module(v1)
base=v1.base;c=base.c;ROLES=v1.ROLES

def limb(body,frames,side,chain,goals,poles):
    """Preserve the native hinge plane rather than driving the shoulder from the knife."""
    ids=[body.ix[n+'_'+side] for n in chain];ui,ei,hi=ids
    p,q=body.world(frames);ip,iq=body.world(body.idle);origin=p[:,ui]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goals-origin);dist=np.clip(np.linalg.norm(goals-origin,axis=1),abs(l1-l2)+.1,(l1+l2)*.985)
    bend=poles-origin;bend=c.unit(bend-axis*np.sum(bend*axis,axis=1)[:,None])
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    elbow=origin+axis*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper=elbow-origin;fore=origin+axis*dist[:,None]-elbow
    ru=ip[ei]-ip[ui];rf=ip[hi]-ip[ei]
    uq=c.frame(upper,fore)*c.frame(ru,rf).inv()*R.from_quat(iq[ui])
    fq=c.frame(fore,upper)*c.frame(rf,ru).inv()*R.from_quat(iq[ei])
    body.set_world_rotations(frames,{ui:uq,ei:fq})
    return c.unit(fore),fq

def leg_helpers(body,frames):
    for side in 'lr':
        for bone,end in [('thigh','calf'),('calf','foot')]:
            i,j=body.ix[bone+'_'+side],body.ix[end+'_'+side]
            reference=R.from_quat(body.ref[i,3:7]);current=R.from_quat(frames[:,i,3:7])
            axis=c.unit(body.ref[j,:3]);ref_axis=reference.apply(axis)
            swing=c.align(np.tile(ref_axis,(len(frames),1)),current.apply(np.tile(axis,(len(frames),1))))
            axial=(reference.inv()*swing.inv()*current).as_rotvec()
            for suffix in ('01','02'):
                key=bone+'_twist_'+suffix+'_'+side
                if key not in body.ix:continue
                k=body.ix[key];station=np.clip(np.linalg.norm(body.ref[k,:3])/np.linalg.norm(body.ref[j,:3]),0.,1.)
                frames[:,k,3:7]=(R.from_rotvec(-(1.-station)*axial)*R.from_quat(body.ref[k,3:7])).as_quat()

def make(body,label,tuning,times):
    n=len(times);size=body.scale/94.;ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin;u=np.clip((times-ready)/spin,0.,1.);exit_u=np.clip((times-stop)/recover,0.,1.)
    entry=base.smooth(times/ready);leave=base.smooth(exit_u)
    pose_weight=entry*(1.-leave);depth=(1.+16.*base.smooth(u))*(1.-leave)
    spin_phase=base.old.arms.phase(u);turns=abs(tuning['turnDegrees'])/360.
    active=base.smooth(u/.12)*(1.-base.smooth((u-.86)/.14))
    f=np.repeat(body.idle[None],n,axis=0);ip,iq=body.world(body.idle)
    # Keep the centre over the support base, with one deliberate descent/rise.
    target=np.tile(ip[body.hip],(n,1));target[:,0]=.7*size*np.sin(2*np.pi*turns*spin_phase)*active
    target[:,1]=(-4.-4.*base.smooth(u))*size
    target[:,2]=ip[body.hip,2]-depth*size
    f[:,body.hip,:3]=ip[body.hip]+(target-ip[body.hip])*pose_weight[:,None]
    pitch=-8.-9.*base.smooth(u)
    desired={}
    for name,amount in [('pelvis',.25),('spine_01',.42),('spine_02',.58),('spine_03',.72),
                        ('spine_04',.88),('spine_05',1.),('neck_01',.35),('neck_02',.25),('head',.18)]:
        if name not in body.ix:continue
        i=body.ix[name]
        q=R.from_euler('x',(pitch*amount)[:,None],degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(iq[i],q.as_quat(),pose_weight[:,None]))
    body.set_world_rotations(f,desired)
    # Shoulder-width support. Neither foot orbits the midline in actor space.
    for side,sign,phase_offset,arrive,depart in [('l',1,0.,(.01,.26),(.22,.50)),('r',-1,.5,(.23,.49),(.01,.29))]:
        foot,ball=body.ix['foot_'+side],body.ix['ball_'+side]
        cycle=2*np.pi*(turns*spin_phase+phase_offset)
        lift=np.maximum(0.,np.sin(cycle))**2*active
        contact=base.smooth((times-arrive[0])/(arrive[1]-arrive[0]))*(1.-base.smooth((times-stop-depart[0])/(depart[1]-depart[0])))
        toe=np.c_[np.full(n,sign*22.*size), (8.+2.5*np.sin(cycle)*active)*size,
                  np.full(n,ip[ball,2])+1.8*size*lift]
        toe=ip[ball]+(toe-ip[ball])*contact[:,None]
        entry_arc=np.sin(np.pi*np.clip((times-arrive[0])/(arrive[1]-arrive[0]),0,1))**2
        exit_arc=np.sin(np.pi*np.clip((times-stop-depart[0])/(depart[1]-depart[0]),0,1))**2
        toe[:,2]+=(6.*entry_arc+5.*exit_arc)*size
        ref_forward=body.tp[ball]-body.tp[foot]
        ref_yaw=np.arctan2(-ref_forward[0],ref_forward[1])
        yaw=np.radians(-sign*(12.+4.*np.sin(cycle)*active))
        heel=R.from_euler('x',(-7.*lift)[:,None],degrees=True)
        q=R.from_euler('z',(yaw-ref_yaw)[:,None])*heel*R.from_quat(body.tq[foot])
        q=R.from_quat(c.slerp(iq[foot],q.as_quat(),contact[:,None]))
        toe_local=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        goal=toe-q.apply(np.tile(toe_local,(n,1)))
        p,_=body.world(f);hip=p[:,body.ix['thigh_'+side]]
        # Both knees advance over their own toes, with an outward bend plane.
        pole=np.c_[np.full(n,sign*28.*size),np.full(n,48.*size),hip[:,2]-28.*size]
        pole=ip[body.ix['calf_'+side]]*(1.-contact[:,None])+pole*contact[:,None]
        limb(body,f,side,('thigh','calf','foot'),goal,pole)
        body.set_world_rotations(f,{foot:q})
    # Both scapulae participate modestly; chest helpers retain their native rest.
    grid=np.linspace(0,1,4097)
    deploy_u=np.interp(150./abs(tuning['turnDegrees']),base.old.arms.phase(grid),grid)
    deploy=base.smooth(u/deploy_u);arm_weight=deploy*(1.-leave)
    p,q=body.world(f);chest=body.ix['spine_05']
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    for side,sign in [('l',1),('r',-1)]:
        i=body.ix['clavicle_'+side]
        idle=torso*idle_torso.inv()*R.from_quat(iq[i])
        open_q=torso*R.from_euler('y',-sign*4.,degrees=True)*R.from_quat(body.tq[i])
        body.set_world_rotations(f,{i:R.from_quat(c.slerp(idle.as_quat(),open_q.as_quat(),arm_weight[:,None]))})
    p,q=body.world(f)
    # A heading frame lets wrists stay shoulder-high as the torso leans.
    forward=torso.apply(np.tile([0,1,0],(n,1)));heading=R.from_euler('z',np.arctan2(-forward[:,0],forward[:,1])[:,None])
    tip=c.unit(np.asarray(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm']))
    grip,lp,lq=v1.left_grip(body);rp,rq=base.native.blade_mount(body)
    banks={}
    for side,sign,mp,mq in [('l',1,lp,lq),('r',-1,rp,rq)]:
        ui,ei,hi=[body.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        hand0=idle_torso.inv().apply(ip[hi]-ip[ui]);elbow0=idle_torso.inv().apply(ip[ei]-ip[ui])
        goal0=p[:,ui]+torso.apply(np.tile(hand0,(n,1)))
        goal1=p[:,ui]+heading.apply(np.tile([sign*.978,.06,-.02],(n,1))*length)
        goal=goal0+(goal1-goal0)*arm_weight[:,None]
        pole0=p[:,ui]+torso.apply(np.tile(elbow0,(n,1)))
        pole1=p[:,ui]+heading.apply(np.tile([sign*.45,-.48,-.12],(n,1))*length)
        # Carry the elbow bend around the changing reach axis. A linear pole
        # crosses that axis while a folded idle arm opens, producing a brief
        # shoulder flip even when the hand follows a smooth path.
        axis0=c.unit(goal0-p[:,ui]);axis1=c.unit(goal1-p[:,ui]);reach_axis=c.unit(goal-p[:,ui])
        bend0=pole0-p[:,ui];bend0=c.unit(bend0-axis0*np.sum(bend0*axis0,axis=1)[:,None])
        bend1=pole1-p[:,ui];bend1=c.unit(bend1-axis1*np.sum(bend1*axis1,axis=1)[:,None])
        carried=c.align(axis0,reach_axis).apply(bend0)
        end_bend=c.align(axis0,axis1).apply(bend0)
        roll=np.arctan2(np.sum(axis1*np.cross(end_bend,bend1),axis=1),np.sum(end_bend*bend1,axis=1))
        bend=R.from_rotvec(reach_axis*(roll*arm_weight)[:,None]).apply(carried)
        pole=p[:,ui]+bend*length
        axis,fq=limb(body,f,side,('upperarm','lowerarm','hand'),goal,pole)
        neutral=fq*R.from_quat(body.ref[hi,3:7])
        full=int(np.flatnonzero(deploy>=1.-1e-8)[0])
        # One bounded forearm bank for the whole take. Let the blade bank follow
        # the palm instead of solving a fixed blade face back into the shoulder.
        candidates=[]
        for angle in np.linspace(-95.,95.,191):
            h=R.from_rotvec(axis[full]*np.radians(angle))*neutral[full]
            vector=(h*mq).apply(tip);local=heading[full].inv().apply(vector)
            flat=c.unit(vector*np.array([1.,1.,0.]))
            tilt=np.degrees(np.arcsin(np.clip(vector[2],-1.,1.)))
            score=tilt*tilt+.025*angle*angle+4000.*max(0.,.28-sign*local[0])**2+800.*max(0.,-.12-sign*local[1])**2
            candidates.append((score,angle))
        angle=min(candidates)[1];banks[side]=angle
        fq=R.from_rotvec(axis*np.radians(angle*arm_weight)[:,None])*fq
        neutral=fq*R.from_quat(body.ref[hi,3:7])
        vector=(neutral*mq).apply(np.tile(tip,(n,1)))
        flat=c.unit(vector*np.array([1.,1.,0.]))
        # The grip is a stable local wrist frame. Re-projecting onto the floor
        # during recovery flips 180 degrees when the blade passes vertical.
        # Solve its small correction once in the deployed pose, then release
        # that same correction continuously into the native idle wrist.
        flat_hand=c.align(vector[full],flat[full])*neutral[full]
        held_local=fq[full].inv()*flat_hand
        hand=fq*R.from_quat(c.slerp(body.idle[hi,3:7],held_local.as_quat(),arm_weight[:,None]))
        body.set_world_rotations(f,{ei:fq,hi:hand})
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=grip[i]
    base.old.right_fingers(body,f,base.old.grip(body))
    base.native.native_twists(body,f);leg_helpers(body,f)
    # Keep the original idle helper offsets at the two outer boundaries only;
    # main-joint motion remains the sole driver through the entire active pose.
    seed=body.idle[None].copy();base.native.native_twists(body,seed);leg_helpers(body,seed)
    for i,name in enumerate(body.names):
        if not any(name.startswith(k+'_twist_') for k in ('upperarm','lowerarm','thigh','calf')):continue
        amount=arm_weight if name.startswith(('upperarm','lowerarm')) else pose_weight
        offset=R.from_quat(body.idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
        f[:,i,3:7]=(R.from_quat(c.slerp([0,0,0,1],offset.as_quat(),(1.-amount)[:,None]))*R.from_quat(f[:,i,3:7])).as_quat()
    for i,name in enumerate(body.names):
        if not (name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_'))):f[[0,-1],i]=body.idle[i]
    base.old.right_fingers(body,f,base.old.grip(body))
    return f,{'forearm_bank_degrees':banks,'lowering_cm':17.*size,'stance_toe_half_width_cm':22.*size}

def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=base.effective_tuning();times,cuts,_,_=base.timeline(tuning)
    report={'version':'Dual whirlwind V2 supported squat and anatomical arms','tuning':tuning,'runtime_tested':False,'bodies':{}}
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        body=c.Body(data);frames,info=make(body,label,tuning,times)
        for k in range(1,len(frames)):frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
        clips={r:{'rate_num':base.RATE,'rate_den':1,'frames':frames[a:b].tolist(),'contact':0.,'release':.999,
            'source':'Native body hinge frames and accepted dual grip','adaptation':'Supported squat with open knee-toe alignment; bilateral native elbow chains, bounded forearm bank, continuous shoulder-hand recovery'} for r,(a,b) in zip(ROLES,cuts)}
        (OUT/(label+'-actions.json')).write_text(json.dumps({'mesh':data['mesh'],'names':body.names,'parents':body.parents,'clips':clips},separators=(',',':')))
        report['bodies'][label]={'mesh':data['mesh'],'previous_roles':{r:active['clips']['Kukri.FullBody.'+r] for r in ROLES},**info}
        print('DUAL_REPAIR_AUTHORED',label,info,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
