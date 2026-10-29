"""V2: native full-body paired cuts with supported elbows and a neutral torso.

The FPS animation supplies handedness, contact windows and sequence length.
Its camera-framed shoulder reach is not a world-body limb target. The two
arms instead follow continuous, separated anatomical arcs on the same clock.
"""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
s=importlib.util.spec_from_file_location('old_dual',ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
c,base,carry=old.c,old.base,old.carry
RATE=120

def smooth(x):
    x=np.clip(x,0.,1.);return x*x*x*(10.+x*(-15.+6.*x))

def ramp(t,a,b):return smooth((t-a)/(b-a))

def curve(t,keys,values):return PchipInterpolator(keys,np.asarray(values,dtype=float),axis=0)(t)

def support(body,t,role):
    f=np.repeat(body.idle[None],len(t),axis=0);ip,iq=body.world(body.idle)
    weight=ramp(t,0.,.22)*(1.-ramp(t,t[-1]-.42,t[-1]))
    keys=[0.,.23,.38,.56,.73,.88,1.08,t[-1]]
    yaw=curve(t,keys,[0.,-16.,6.,12.,15.,-8.,-8.,0.])
    if role=='Slash2':yaw=-yaw*.65
    desired={}
    for name,pitch,turn in [('pelvis',0.,.20),('spine_01',-4.,.45),('spine_02',-5.,.60),
        ('spine_03',-5.,.75),('spine_04',-5.,.90),('spine_05',-5.,1.),('neck_01',-2.,.25),('neck_02',-1.,.20),('head',0.,.15)]:
        if name not in body.ix:continue
        i=body.ix[name];target=R.from_euler('xyz',np.c_[np.full(len(t),pitch),np.zeros(len(t)),yaw*turn],degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(np.tile(iq[i],(len(t),1)),target.as_quat(),weight[:,None]))
    body.set_world_rotations(f,desired)
    # Lift out of the low carry without moving the planted feet. A small
    # transfer follows each arm; no prolonged single-attack folded torso.
    size=body.scale/94.
    f[:,body.hip,:3]+=np.c_[curve(t,keys,[0.,-1.,-2.,0.,1.,2.,0.,0.]),np.full(len(t),2.),np.full(len(t),6.)]*weight[:,None]*size
    for side,sign in [('r',-1.),('l',1.)]:
        foot=body.ix['foot_'+side];knee=body.ix['calf_'+side]
        goal=np.tile(ip[foot],(len(t),1));pole=np.tile(ip[knee],(len(t),1))
        pole+=np.tile([sign*2.,5.,0.],(len(t),1))*weight[:,None]*size
        body.solve(f,[n+'_'+side for n in ('thigh','calf','foot')],goal,pole,R.from_quat(np.tile(iq[foot],(len(t),1))))
    return f,weight

def arm_paths(body,f,t,role,side,weight):
    """Shoulder-relative reach in upright actor axes, scaled by native arm."""
    ip,iq=body.world(body.idle);p,q=body.world(f)
    ui,ei,hi=[body.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(ip[ei]-ip[ui])+np.linalg.norm(ip[hi]-ip[ei]);sign=1. if side=='l' else -1.
    rest=ip[hi]-ip[ui]
    # Right horizontal cut travels to the left. The second is a reverse
    # diagonal downcut. The offhand follows the same semantics, mirrored in
    # spatial reach only, after the actual FPS contact offset.
    delay=0. if side=='r' else (56./120 if role=='Slash1' else .5)
    x=np.clip(t-delay,0.,1.266666667)
    if role=='Slash1':
        keys=[0.,.18,.28,.357,.45,.58,.78,1.02,1.266666667]
        local=np.array([[-.14,.50,-.50],[-.54,.36,.02],[-.48,.62,-.08],[.08,.88,-.17],
            [.58,.64,-.35],[.61,.44,-.60],[-.05,.40,-.78],[-.20,.40,-.68],[-.14,.50,-.50]])
        directions=np.array([[-.1,.7,.7],[-.45,.65,.6],[-.4,.88,.2],[0.,1.,.05],[.5,.86,-.12],
            [.5,.75,-.40],[-.12,.55,-.82],[-.12,.7,.7],[-.1,.7,.7]])
    else:
        keys=[0.,.18,.29,.38,.47,.60,.80,1.04,1.266666667]
        local=np.array([[-.14,.50,-.50],[.45,.51,.05],[.47,.66,.02],[.05,.88,-.24],
            [-.49,.65,-.58],[-.47,.38,-.76],[-.15,.35,-.78],[-.15,.42,-.65],[-.14,.50,-.50]])
        directions=np.array([[-.1,.7,.7],[.30,.55,.78],[.32,.70,.65],[.05,.98,.18],[-.35,.82,-.45],
            [-.40,.62,-.68],[-.15,.50,-.85],[-.12,.7,.7],[-.1,.7,.7]])
    if side=='l':local[:,0]*=-1.;directions[:,0]*=-1.
    local=curve(x,keys,local)*length;directions=c.unit(curve(x,keys,directions))
    # The waiting hand stays low on its own side, then loads before its cut.
    # The leading hand finishes low before the other arm crosses the centre.
    if side=='l':
        engage=ramp(t,max(0.,delay-.14),delay+.18)
        local=np.array([sign*.16,.42,-.65])*length+(local-np.array([sign*.16,.42,-.65])*length)*engage[:,None]
    else:
        hang=ramp(t,.62,.86)*(1.-ramp(t,t[-1]-.42,t[-1]))
        local=local*(1.-hang[:,None])+np.array([-.18,.30,-.81])*length*hang[:,None]
    local=rest+(local-rest)*weight[:,None]
    local*=np.minimum(1.,.94*length/np.maximum(np.linalg.norm(local,axis=1),1e-8))[:,None]
    goal=p[:,ui]+local
    # The native elbow remains outside the flank and below the wrist arc.
    pole=p[:,ui]+np.array([sign*.43,.14,-.56])*length
    axis=c.unit(goal-p[:,ui]);bend=c.unit(pole-p[:,ui]-axis*np.sum((pole-p[:,ui])*axis,axis=1)[:,None])
    rest_axis=c.unit(ip[hi]-ip[ui]);rest_bend=c.unit(ip[ei]-ip[ui]-rest_axis*np.dot(ip[ei]-ip[ui],rest_axis))
    transported=c.align(np.tile(rest_axis,(len(t),1)),axis).apply(np.tile(rest_bend,(len(t),1)))
    # The carry elbow points backward. Restricting its transported pole to
    # 65 degrees traps a forward cut on the inner/chest side of the arm.
    # Move to the anatomical outer pole on the shortest arc; no unwrapped
    # multi-turn angle is multiplied into the entry/recovery envelope.
    angle=np.arctan2(np.sum(axis*np.cross(transported,bend),axis=1),np.sum(transported*bend,axis=1))*weight
    bend=R.from_rotvec(axis*angle[:,None]).apply(transported)
    return goal,bend,directions

def arm(body,f,t,role,side,weight):
    # Clear the WHOLE arm branch first, including skin correction bones. A
    # donor corrective offset cannot survive after replacing its major joints.
    ci=body.ix['clavicle_'+side]
    for i in range(len(body.names)):
        par=i
        while par>=0 and par!=ci:par=body.parents[par]
        if par==ci:
            f[:,i]=body.idle[i]
            if not body.names[i].startswith(('thumb_','index_','middle_','ring_','pinky_','hand_')) and i not in (body.ix['upperarm_'+side],body.ix['lowerarm_'+side]):
                f[:,i]=c.blend(f[:,i],np.repeat(body.ref[i][None],len(t),axis=0),weight[:,None])
    ip,iq=body.world(body.idle);p,q=body.world(f)
    # The scapula follows the chest with a small lift, not a weapon-driven spin.
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    goal,bend,directions=arm_paths(body,f,t,role,side,weight);origin=p[:,ui]
    n=len(t);zero=np.zeros(n)
    nominal=R.from_quat(q[:,ci])*R.from_quat(body.ref[ui,3:7])
    def native_chain(bank):
        # Position is the analytic two-link solution. Skin orientation uses
        # the native shoulder's shortest swing, rather than carrying the
        # old backward-guard hinge plane through a forward attack.
        e,_,_=old.solve(body,side,origin,goal,bend,zero,zero,ip,iq)
        u,v=e-origin,goal-e
        uq=c.align(nominal.apply(np.tile(body.ref[ei,:3],(len(t),1))),u)*nominal
        neutral_fore=uq*R.from_quat(body.ref[ei,3:7])
        fq=c.align(neutral_fore.apply(np.tile(body.ref[hi,:3],(len(t),1))),v)*neutral_fore
        # Preserve exact carry while entering/leaving this anatomical frame.
        _,old_u,old_f=old.solve(body,side,origin,goal,bend,zero,zero,ip,iq)
        uq=R.from_quat(c.slerp(old_u.as_quat(),uq.as_quat(),weight[:,None]))
        fq=R.from_quat(c.slerp(old_f.as_quat(),fq.as_quat(),weight[:,None]))
        fq=R.from_rotvec(c.unit(v)*bank[:,None])*fq
        return e,uq,fq
    elbow,upper,fore=native_chain(zero)
    mp,mq=base.native.blade_mount(body) if side=='r' else carry.dual.v1.left_grip(body)[1:]
    wrist=R.from_quat(body.idle[hi,3:7]);tip=c.unit(np.array([6.18,0.,26.29]))
    bank_values=np.radians(np.linspace(-65.,65.,131));cost=np.empty((n,len(bank_values)))
    v=c.unit(goal-elbow)
    # A single bounded pronation angle supports the knife. The elbow plane
    # is never rotated again to chase a camera-oriented palm target.
    for k in range(n):
        candidates=R.from_rotvec(np.tile(v[k],(len(bank_values),1))*(bank_values*weight[k])[:,None])*fore[k]
        vec=(candidates*wrist*mq).apply(np.tile(tip,(len(bank_values),1)))
        error=np.arccos(np.clip(vec@directions[k],-1.,1.))
        cost[k]=error**2+.18*bank_values**2
    diff=bank_values[:,None]-bank_values[None];transition=2.*diff*diff;transition[np.abs(diff)>np.radians(4.01)]=np.inf
    back=np.zeros_like(cost,dtype=int);score=cost[0].copy()
    for k in range(1,n):
        values=score[:,None]+transition;back[k]=np.argmin(values,axis=0);score=cost[k]+values[back[k],np.arange(len(bank_values))]
    idx=np.empty(n,int);idx[-1]=score.argmin()
    for k in range(n-1,0,-1):idx[k-1]=back[k,idx[k]]
    bank=gaussian_filter1d(bank_values[idx],2.,mode='nearest')*weight
    _,upper,fore=native_chain(bank)
    hand=fore*wrist;vec=(hand*mq).apply(np.tile(tip,(n,1)))
    swing=c.align(vec,directions).as_rotvec();magnitude=np.linalg.norm(swing,axis=1)
    swing*=np.minimum(1.,np.radians(16.)/np.maximum(magnitude,1e-8))[:,None]*weight[:,None]
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:R.from_rotvec(swing)*hand})

def main():
    inputs=json.loads((old.OUT/'inputs.json').read_text());cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Dual combo V2 native arms and upright support',bodies={},first_person_changed=False,runtime_tested=False)
    for label,source in inputs.items():
        data=base.rig.DATA[label];body=c.Body(data);body.idle=np.array(source['clips']['Dual.Idle']['frames'][0])
        active=cfg if label=='jason' else cfg['body_variants'][label];clips={}
        for role,name in [('Slash1','DualAttack'),('Slash2','DualAttack2')]:
            fp=old.fps_source(name);t=np.arange(len(fp['p']))/RATE;f,w=support(body,t,role)
            for side in ('r','l'):arm(body,f,t,role,side,np.ones(len(t)))
            # Return the complete native arm pose to carry. Do not pull its
            # wrist goal behind the torso while fading a +/-pi elbow-pole
            # angle: that crossed the branch cut and flipped the recovery.
            for i in range(len(body.names)):
                par=i
                while par>=0 and par not in (body.ix['clavicle_r'],body.ix['clavicle_l']):par=body.parents[par]
                if par>=0:f[:,i]=c.blend(np.repeat(body.idle[i][None],len(f),axis=0),f[:,i],w[:,None])
            old.helpers(body,f);f[0]=body.idle;f[-1]=body.idle
            cdata=json.loads((old.OUT/(label+'-actions.json')).read_text())['clips']['Dual.'+role]
            clips['Dual.'+role]={**cdata,'frames':carry.continuous(f).tolist(),
                'adaptation':'Native mesh reference, whole arm branch reset, supported independent elbows, bounded pronation and low waiting hand; upright full body on original FPS dual clock'}
            print('COMBO_V2_AUTHORED',label,role,flush=True)
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(previous_roles={r:active['clips']['Kukri.FullBody.'+r] for r in clips},native_reference=data['authoring_reference_source'])
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
