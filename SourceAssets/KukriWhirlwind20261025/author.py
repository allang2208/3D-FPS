"""Native two-turn kukri performance from CC0 Sword Regular C.

The actor owns signed world rotation. Foot anchors are authored against that
same angular clock and converted back into actor space, so a stance foot holds
its position while the other foot travels around it. C supplies torso motion;
the native single-hand mount and closed guard supply the hand contract.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
BASE=ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


c=module('kukri_whirl_body',BASE/'author.py')
guard=module('kukri_whirl_fingers',ROOT/'SourceAssets/KukriThrustHand20261025/author.py')
heavy=module('kukri_whirl_fit',ROOT/'SourceAssets/KukriHeavy20261025/author.py')
SOURCE=json.loads((OUT/'source-c.json').read_text())
TUNING=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']


def phase(u):
    # RuneSwordWhirlwindFeel.h NormalizedPhase: integrate the eased velocity.
    a,b=.12,.18
    area=1-.5*(a+b)
    ramp=lambda v:v*v*v-.5*v*v*v*v
    return np.where(u<a,a*ramp(u/a)/area,
                    np.where(u>1-b,1-b*ramp((1-u)/b)/area,(u-.5*a)/area))


def blade(tip,edge):
    tip=c.unit(np.asarray(tip));edge=c.unit(np.asarray(edge)-tip*np.sum(tip*edge,axis=-1,keepdims=True))
    return c.frame(edge,np.cross(tip,edge))


def neutral_source(body):
    raw=body.retarget(np.asarray(SOURCE['frames']))
    p,q=body.world(raw)
    direction=(R.from_quat(q[:,body.hip])*R.from_quat(body.tq[body.hip]).inv()).apply(np.tile([0.,1.,0.],(len(raw),1)))
    yaw=np.unwrap(np.arctan2(-direction[:,0],direction[:,1]))
    # Strip the donor's overall yaw once at the pelvis; retain its relative
    # chest, shoulder and limb motion. Never add the source turn to actor yaw.
    body.set_world_rotations(raw,{body.hip:R.from_euler('z',-yaw[:,None])*R.from_quat(q[:,body.hip])})
    raw[:,body.hip,:2]=0.
    return raw,yaw


def fit_legs(body,frames,goals,rotations,poles):
    p,_=body.world(frames);drop=np.zeros(len(frames))
    for side in 'lr':
        h,k,a=[p[:,body.ix[n+'_'+side]] for n in ('thigh','calf','foot')]
        reach=(np.linalg.norm(k-h,axis=1)+np.linalg.norm(a-k,axis=1))*.990
        goal=goals[side]
        maximum=goal[:,2]+np.sqrt(np.maximum(1.,reach**2-np.sum((goal[:,:2]-h[:,:2])**2,axis=1)))
        drop=np.maximum(drop,h[:,2]-maximum)
    frames[:,body.hip,2]-=drop
    for side in 'lr':
        body.solve(frames,[n+'_'+side for n in ('thigh','calf','foot')],goals[side],poles[side],rotations[side])


def spin_feet(body,frames,angular,size):
    ip,iq=body.world(body.idle)
    direction=np.sign(TUNING['turnDegrees']);turns=abs(TUNING['turnDegrees'])/360
    turns_done=turns*angular;actor=direction*2*np.pi*turns_done
    half=2*turns_done
    goals={};rotations={};poles={}
    for side,offset in [('l',0.),('r',.5)]:
        x=half-offset;n=np.floor(x);f=x-n
        swing=np.clip((f-.5)*2,0,1)
        centre=(n+offset+.25)/2
        anchor=direction*2*np.pi*(centre+.5*c.ease(swing))
        relative=anchor-actor
        yaw=R.from_euler('z',relative[:,None])
        # Eight alternating landings across 720 degrees. During stance the
        # anchor and foot yaw are constant in world space; flight follows an
        # outside arc, avoiding a straight chord through the other ankle.
        lift=np.sin(np.pi*swing)**2
        radius=21*size*(1+.12*lift)
        points=np.c_[(1 if side=='l' else -1)*radius,np.zeros(len(f)),np.zeros(len(f))]
        points=yaw.apply(points)
        heel=np.where(f<.5,-9*np.sin(np.pi*f*2)**2,7*np.sin(np.pi*swing))
        foot=body.ix['foot_'+side];ball=body.ix['ball_'+side]
        base=yaw*R.from_quat(np.tile(iq[foot],(len(f),1)))
        rot=yaw*R.from_euler('x',heel[:,None],degrees=True)*R.from_quat(np.tile(iq[foot],(len(f),1)))
        toe=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        baseline=base.apply(np.tile(toe,(len(f),1)));actual=rot.apply(np.tile(toe,(len(f),1)))
        points[:,2]=ip[ball,2]-baseline[:,2]+6*size*lift
        points+=baseline-actual
        goals[side]=points;rotations[side]=rot
        knee=R.from_euler('z',(.55*relative)[:,None]).apply(np.tile([27 if side=='l' else -27,38,-30],(len(f),1)))*size
        poles[side]=frames[:,body.hip,:3]+knee
    fit_legs(body,frames,goals,rotations,poles)
    return goals,rotations


def set_fist(body,frames,fist,weight):
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.split('_')[0] in ('thumb','index','middle','ring','pinky'):
            frames[:,i,3:7]=c.slerp(frames[:,i,3:7],fist[i,3:7],weight[:,None])


def step_transition(body,frames,times,start,end,start_q,end_q,windows,size):
    goals={};rots={};poles={}
    sp,sq=body.world(frames[0]);ep,eq=body.world(frames[-1])
    for side in 'lr':
        a,b=windows[side];v=np.clip((times-a)/(b-a),0,1);w=c.ease(v)
        goals[side]=start[side]*(1-w[:,None])+end[side]*w[:,None]
        goals[side][:,2]+=np.sin(np.pi*v)**2*(9 if side=='l' else 6)*size
        rots[side]=R.from_quat(c.slerp(start_q[side],end_q[side],w[:,None]))
        knee=body.ix['calf_'+side]
        wbody=c.ease(times/times[-1])
        poles[side]=sp[knee]*(1-wbody[:,None])+ep[knee]*wbody[:,None]
    fit_legs(body,frames,goals,rots,poles)


def make_body(label,data,previous,fist_source):
    body=c.Body(data);size=body.scale/94.
    ip,iq=body.world(body.idle);hip=ip[body.hip];ri=body.ix['hand_r'];li=body.ix['hand_l']
    neutral,source_yaw=neutral_source(body)
    anchor=c.sample(neutral,.16)
    u=np.linspace(0,1,129);angular=phase(u)
    turns=abs(TUNING['turnDegrees'])/360
    cycles=turns*angular;cycle=cycles-np.floor(cycles)
    frames=[]
    for t in cycle:
        raw=c.sample(neutral,.10+.57*t)
        w=c.ease(t/.18)*(1-c.ease((t-.78)/.22))
        frames.append(c.blend(body.idle,c.blend(anchor,raw,w),.48))
    loop=np.asarray(frames)
    half=2*cycles
    loop[:,body.hip,:3]=hip+np.c_[3*np.sin(2*np.pi*half),1.5*np.cos(2*np.pi*half),-5+1.8*np.cos(4*np.pi*half)]*size
    feet,footq=spin_feet(body,loop,angular,size)
    p,q=body.world(loop);hips=p[:,body.hip]
    turn_wave=np.sin(2*np.pi*cycles)
    right=np.c_[-52-3*turn_wave**2,8+8*turn_wave,36+4*np.cos(2*np.pi*cycles)]*size
    left=np.c_[22+2*turn_wave,27-3*turn_wave,45+2*np.cos(2*np.pi*cycles)]*size
    # Keep a small portion of C's native arm rhythm together with its torso,
    # while the blade remains on the right-side sweep used by the skill.
    right=.88*right+.12*(p[:,ri]-hips)
    left=.94*left+.06*(p[:,li]-hips)
    tips=np.c_[-np.ones(len(u)),.12+.10*turn_wave,.04+.07*np.sin(4*np.pi*cycles)]
    bladeq=blade(tips,np.tile([0.,1.,0.],(len(u),1)))
    rq=bladeq*body.blade_local.inv()
    lbase=R.from_euler('xz',[-12,-10],degrees=True)*R.from_quat(iq[li])
    lq=R.from_euler('z',(6*turn_wave)[:,None],degrees=True)*R.from_quat(np.tile(lbase.as_quat(),(len(u),1)))
    for side,goal,rot,pole in [('r',right,rq,[-39,-7,26]),('l',left,lq,[40,8,24])]:
        body.solve(loop,[n+'_'+side for n in ('upperarm','lowerarm','hand')],hips+goal,
                   hips+np.asarray(pole)*size,rot)
    fist=guard.native_fist(body,fist_source)
    set_fist(body,loop,fist,np.ones(len(u)))
    loop=body.twists(loop)
    # Two whole turns finish on exactly the same prepared support pose.
    loop[-1]=loop[0]
    lp,lqworld=body.world(loop)

    # Wind up into the first planted anchor. The two feet prepare sequentially.
    st=np.arange(31)/60
    start=np.array([c.blend(body.idle,loop[0],c.ease(t/.5)) for t in st])
    counter=10*np.sin(np.pi*st/.5)**2
    _,sq=body.world(start)
    body.set_world_rotations(start,{body.hip:R.from_euler('z',counter[:,None],degrees=True)*R.from_quat(sq[:,body.hip])})
    starts={s:ip[body.ix['foot_'+s]] for s in 'lr'}
    ends={s:lp[0,body.ix['foot_'+s]] for s in 'lr'}
    qs={s:iq[body.ix['foot_'+s]] for s in 'lr'}
    qe={s:lqworld[0,body.ix['foot_'+s]] for s in 'lr'}
    step_transition(body,start,st,starts,ends,qs,qe,{'l':(.05,.29),'r':(.27,.49)},size)
    set_fist(body,start,fist,c.ease((st-.03)/.23))
    start=body.twists(start);start[0]=body.idle;start[-1]=loop[0]

    # C's recovery supplies the torso settling, with native hand/foot targets
    # returning to the current stance. No extra global spin is baked here.
    et=np.arange(33)/60;ev=et/et[-1]
    end=[]
    for v in ev:
        raw=c.blend(body.idle,c.sample(neutral,.72+1.28*v),.48)
        f=c.blend(loop[-1],raw,c.ease(v/.30))
        end.append(c.blend(f,body.idle,c.ease((v-.40)/.60)))
    end=np.asarray(end)
    end[:,body.hip,:3]=lp[-1,body.hip]*(1-c.ease(ev)[:,None])+hip*c.ease(ev)[:,None]
    end[:,body.hip,2]-=2.5*size*np.sin(np.pi*ev)**2
    step_transition(body,end,et,ends,starts,qe,qs,{'r':(.02,.24),'l':(.22,.51)},size)
    ep,_=body.world(end);eh=ep[:,body.hip]
    keys=[0.,.14,.32,et[-1]]
    for side in 'rl':
        j=body.ix['hand_'+side]
        offsets=np.array([lp[-1,j]-lp[-1,body.hip],np.array([-43,16,38] if side=='r' else [25,30,43])*size,
                          np.array([-34,8,29] if side=='r' else [27,40,31])*size,ip[j]-hip])
        goal=eh+PchipInterpolator(keys,offsets)(et)
        if side=='r':
            qmid=(blade(np.array([-.45,.86,.23]),np.array([0.,1.,0.]))*body.blade_local.inv()).as_quat()
            quats=np.array([lqworld[-1,j],qmid,c.slerp(qmid,iq[j],.65),iq[j]])
        else:quats=np.array([lqworld[-1,j],lqworld[-1,j],c.slerp(lqworld[-1,j],iq[j],.6),iq[j]])
        r=heavy.rotations(keys,quats,et)
        knee=body.ix['lowerarm_'+side]
        pole=lp[-1,knee]*(1-c.ease(ev)[:,None])+ip[knee]*c.ease(ev)[:,None]
        body.solve(end,[n+'_'+side for n in ('upperarm','lowerarm','hand')],goal,pole,r)
    set_fist(body,end,fist,1-c.ease((ev-.25)/.65))
    end=body.twists(end)
    for i,v in enumerate(ev):end[i]=c.blend(end[i],body.idle,c.ease((v-.80)/.20))
    end[0]=loop[-1];end[-1]=body.idle
    clips={}
    for role,f,rate in [('Whirlwind.Start',start,60),('Whirlwind.Loop',loop,120),('Whirlwind.End',end,60)]:
        clips[role]=dict(frames=f.tolist(),rate=rate,loop=False,contact=.4,release=.7,
            source=SOURCE['asset'],adaptation='CC0 C torso rhythm with overall donor yaw removed; native blade-side arm and closed guard; signed angular-clock foot anchors, eight alternating support steps across two turns; continuous phase endpoints.')
    (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips),separators=(',',':')))
    return dict(mesh=data['mesh'],skeleton=data['skeleton'],previous_roles=previous,
        source_yaw_removed_degrees=[float(np.degrees(source_yaw[0])),float(np.degrees(source_yaw[-1]))],
        source_active_range=[.10,.67],source_recovery_range=[.72,2.],turn_degrees=TUNING['turnDegrees'],
        alternating_support_steps=int(turns*4),actor_owns_rotation=True,matched_phase_endpoints=True,
        clips={k:dict(frames=len(v['frames']),rate=v['rate'],seconds=(len(v['frames'])-1)/v['rate']) for k,v in clips.items()})


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    fist=json.loads((ROOT/'SourceAssets/UnarmedIdle20261001/full-pose.json').read_text())
    receipt=dict(bodies={},source_license='CC0 Quaternius UAL2',source=SOURCE['asset'],
        tuning={k:TUNING[k] for k in ('readySeconds','spinSeconds','recoverSeconds','turnDegrees')},
        angular_clock=dict(acceleration=.12,braking=.18),runtime_tested=False,rendered=False,
        gameplay_changed=False,first_person_changed=False)
    for label,data in c.INPUT['targets'].items():
        section=cfg if label=='jason' else cfg['body_variants'][label]
        previous={k:section['clips']['Kukri.FullBody.'+k] for k in ('Whirlwind.Start','Whirlwind.Loop','Whirlwind.End')}
        receipt['bodies'][label]=make_body(label,data,previous,fist)
        print('KUKRI_WHIRLWIND_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
