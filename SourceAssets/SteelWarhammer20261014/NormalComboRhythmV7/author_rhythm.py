"""Warhammer normal combo V6: flowing, non-linear playback of the accepted poses.

Pose sources are the accepted clips (NormalComboV4 Slash1/Slash3, V5 hand-swap
Slash2). Their joint poses are NOT re-solved. The clip clock is rebuilt from
the motion arc length (hammer head + hands + elbows), so the old pickaxe holds
(start stall, dead load hold, follow-through freeze) vanish and every segment
gets an explicit velocity profile:
  load (quick pickup, soft arrival) -> drifting apex -> accelerating release
  -> contact (0.97 s, unchanged) -> decelerating follow-through -> settle.
Per stage cadence: stage 1 standard, stage 2 snappier release (it already
carries the hand swap), stage 3 heavier/longer release and longer hit stop.
Layers on top (P4):
  * momentum carry: after a miss the whole arm+hammer rig (rigid, like V4's
    carry) keeps travelling with the cut; after a hit a short recoil.
  * hammer lag: in the release the hammer trails the hands by up to 6 deg and
    snaps through exactly at contact (wrists solved with native lengths).
  * the grip loosens slightly at the apex and closes into the release.
Gameplay timing is unchanged: contact 0.97 s, swing 1.75 s, hit clip 0.80 s.
Writes ProductionBluntComboTiming.h (apex/turn/chain/whoosh clip seconds).
"""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
PLAN='--plan' in sys.argv
FPS=300;SWING=1.75;CONTACT=.97;RECOVER=.80
V4=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
V5=P.parent/'NormalComboSwapV5/Warhammer_Combo_Swap_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(V4));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
bpy.data.actions['A_Warhammer_Slash2'].name='V4_A_Warhammer_Slash2_Replaced'
with bpy.data.libraries.load(str(V5),link=False) as (src,dst):dst.actions=['A_Warhammer_Slash2']
SOURCES=['A_Warhammer_Slash1','A_Warhammer_Slash2','A_Warhammer_Slash3']
for name in SOURCES:
    if name not in bpy.data.actions:raise RuntimeError('Missing accepted source '+name)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindInertiaV8/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'sat','smooth','rigid','frame','axial'}],type_ignores=[]),'<native_grip_support>','exec'))
roll_state={}
def solve_arm(out,ref,target,side,rigid_guide=False):
    """V8/V5 full-chain solver (native lengths, twist bones). The elbow guide is
    the reference elbow carried by the wrist translation (lag: tiny palm turns)
    or by the whole rigid wrist change (miss swing-on about the shoulders, so the
    forearm turns with the hammer instead of folding the wrist)."""
    U,L,H,C=[x+'_'+side for x in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[ref[n].translation for n in (U,L,H)];u0,l0=e0-s0,h0-e0
    normal=u0.cross(l0).normalized();d=target@ref[H].inverted();dq=d.to_quaternion()
    h=target.translation;ideal_e=d@e0 if rigid_guide else e0+(h-h0)
    ideal_s=ideal_e-(ideal_e-s0).normalized()*u0.length
    support=ideal_s-s0
    support*=.055/math.sqrt(.055**2+support.length_squared)
    s=s0+support;reach=h-s;limit=(u0.length+l0.length)*.96
    if reach.length>limit:s+=reach.normalized()*(reach.length-limit);reach=h-s
    axis=reach.normalized();distance=reach.length
    along=(u0.length**2-l0.length**2+distance**2)/(2*distance)
    radius=math.sqrt(max(0.,u0.length**2-along**2));circle=s+axis*along
    guide=ideal_e-circle;guide-=axis*guide.dot(axis)
    if guide.length<1e-6:
        guide=dq@(e0-s0);guide-=axis*guide.dot(axis)
    e=circle+guide.normalized()*radius;upper=e-s;fore=h-e
    plane=upper.cross(fore).normalized();du=frame(upper,plane)@frame(u0,normal).inverted()
    df=(du@l0).rotation_difference(fore)@du
    full=(dq@l0).rotation_difference(fore)@dq;roll=axial(full@df.inverted(),fore.normalized())
    if side in roll_state:roll=roll_state[side]+((roll-roll_state[side]+math.pi)%(2*math.pi)-math.pi)
    roll_state[side]=roll
    out[C]=ref[C].copy();out[C].translation+=s-s0
    out[U]=rigid(s,du@ref[U].to_quaternion());out[L]=rigid(e,df@ref[L].to_quaternion());out[H]=target
    for index in ('01','02'):
        n='upperarm_twist_'+index+'_'+side
        out[n]=rigid(s+du@(ref[n].translation-s0),du@ref[n].to_quaternion())
        n='lowerarm_twist_'+index+'_'+side
        out[n]=rigid(e+df@(ref[n].translation-e0),Quaternion(fore.normalized(),roll*STATIONS[side][n])@df@ref[n].to_quaternion())

def sample(action,t):
    a=bpy.data.actions[action];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    f=max(0.,min(SWING,t))*FPS;scene.frame_set(int(f),subframe=f-int(f))
    return {b.name:b.matrix.copy() for b in rig.pose.bones}
idle=sample('A_Warhammer_Slash1',0.)
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
pts=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
head=[p for p in pts if p.z>.875];HEAD=sum(head,Vector())/len(head)
grip_idle={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in 'lr'}
PIVOT_LOCAL=Vector((0.,0.,(grip_idle['l'].translation.z+grip_idle['r'].translation.z)*.5))
CARRY_PIVOT=(idle['clavicle_l'].translation+idle['clavicle_r'].translation)*.5

def hermite(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    for a,b in zip(keys,keys[1:]):
        if t<=b[0]:
            span=b[0]-a[0];u=(t-a[0])/span
            return (2*u**3-3*u*u+1)*a[1]+(u**3-2*u*u+u)*span*a[2]+(-2*u**3+3*u*u)*b[1]+(u**3-u*u)*span*b[2]
    return keys[-1][1]
def hseg(u,m0,m1):
    u=sat(u);return (u**3-2*u*u+u)*m0+(-2*u**3+3*u*u)+(u**3-u*u)*m1
def settle(u,gamma):
    """Zero-velocity ends, quicker departure and a longer landing."""
    u=sat(u)**gamma;return u*u*u*(10+u*(-15+6*u))

# Per-stage cadence (P5). Clip seconds; contact stays 0.97. 'over' is the miss
# follow-through: the arms keep swinging about the shoulders after contact.
# V7 rhythm (user: V6 release too slow, too little force, read as linear):
# heavy load -> held tension beat (slow drift) -> explosive release whose speed
# is packed into its last frames (power curve) -> hard impact -> heavy return.
# 'hold' / 'release' are seconds, 'p' the release power, 'hold_frac' the share
# of the load path still drifting during the tension beat.
STAGE=[
 {'hold':.10,'release':.13,'p':3.0,'hold_frac':.035,'load_m0':.55,'gamma':.90,'hit_stop':.08,
  'carry':(6.,3.,-4.),'lag':8.,'over':34.,'whoosh_lead':.095,'recoil':-.35},
 {'hold':.06,'release':.11,'p':2.8,'hold_frac':.03,'load_m0':.60,'gamma':.80,'hit_stop':.07,
  'carry':(-6.,-3.,-4.),'lag':8.,'over':34.,'whoosh_lead':.085,'recoil':-.30},
 {'hold':.15,'release':.14,'p':3.5,'hold_frac':.04,'load_m0':.45,'gamma':1.0,'hit_stop':.12,
  'carry':(0.,0.,-7.),'lag':8.,'over':40.,'whoosh_lead':.105,'recoil':-.45}]
for prm in STAGE:prm['apex']=round(CONTACT-prm['release'],4);prm['hold_start']=round(prm['apex']-prm['hold'],4)
OVER_RETURN=.55
W_HEAD,W_HAND,W_ELBOW=1.,1.5,.6
SRC_N=round(SWING*FPS)

def profile(action):
    frames=[sample(action,i/FPS) for i in range(SRC_N+1)]
    hp=[f['WPN_root']@HEAD for f in frames]
    cum=[0.];hs=[0.]
    for i in range(1,len(frames)):
        a,b=frames[i-1],frames[i]
        d=W_HEAD*(hp[i]-hp[i-1]).length+sum(W_HAND*(b['hand_'+s].translation-a['hand_'+s].translation).length+
            W_ELBOW*(b['lowerarm_'+s].translation-a['lowerarm_'+s].translation).length for s in 'lr')
        cum.append(cum[-1]+d);hs.append((hp[i]-hp[i-1]).length*FPS)
    return frames,cum,hs
def inverse(cum,ell):
    """Source clip seconds at arc length ell (first time it is reached)."""
    lo,hi=0,len(cum)-1
    if ell<=cum[0]:return 0.
    if ell>=cum[-1]:return hi/FPS
    while hi-lo>1:
        mid=(lo+hi)//2
        if cum[mid]<ell:lo=mid
        else:hi=mid
    span=cum[hi]-cum[lo];u=(ell-cum[lo])/span if span>1e-12 else 0.
    return (lo+u)/FPS
def L_at(cum,t):
    f=t*FPS;i=min(len(cum)-2,int(f));u=f-i;return cum[i]+(cum[i+1]-cum[i])*u

stage_data=[];stage_index={id(p):i for i,p in enumerate(STAGE)}
for stage,action in enumerate(SOURCES):
    frames,cum,hs=profile(action);prm=STAGE[stage]
    c_i=round(CONTACT*FPS)
    # Release start: last slow source frame before the downswing burst.
    rel=next(i for i in range(c_i,0,-1) if hs[i]<.3 and i<c_i-3)
    turn=next(i for i in range(c_i+1,SRC_N) if hs[i]<.3)
    L0,La,Lc,Lt,Le=0.,cum[rel],cum[c_i],cum[turn],cum[-1]
    apex=prm['apex'];h0=prm['hold_start'];dt_load=h0;dt_hold=apex-h0;dt_rel=CONTACT-apex
    Lh=La*(1-prm['hold_frac'])
    v_hold=(La-Lh)/dt_hold
    m1_load=v_hold*dt_load/Lh
    a_rel=min(.5,v_hold*dt_rel/(Lc-La))
    v_contact=(a_rel+(1-a_rel)*prm['p'])*(Lc-La)/dt_rel
    def ell(t,La=La,Lh=Lh,Lc=Lc,Lt=Lt,Le=Le,apex=apex,h0=h0,dt_load=dt_load,dt_hold=dt_hold,dt_rel=dt_rel,m1_load=m1_load,a_rel=a_rel,prm=prm,sd=None):
        if t<=h0:return Lh*hseg(t/dt_load,prm['load_m0'],m1_load)
        # Tension beat: the load keeps sinking at a crawl, never a dead stop.
        if t<=apex:return Lh+(La-Lh)*(t-h0)/dt_hold
        # Explosive release: speed packed into the last frames, peak at contact.
        if t<=CONTACT:
            u=(t-apex)/dt_rel;return La+(Lc-La)*(a_rel*u+(1-a_rel)*u**prm['p'])
        turn_new=stage_data[stage_index[id(prm)]]['turn_new']
        # The short source follow-through spreads over the overshoot; the
        # source return only begins at the overshoot extreme.
        if t<=turn_new:return Lc+(Lt-Lc)*(1-(1-sat((t-CONTACT)/(turn_new-CONTACT)))**3)
        return Lt+(Le-Lt)*settle((t-turn_new)/(SWING-turn_new),prm['gamma'])
    dt_follow=0.;turn_new=CONTACT+.10
    hit_follow=.16;hs_hold=prm['hit_stop']
    def ell_hit(u,Lc=Lc,Lt=Lt,Le=Le,hs_hold=hs_hold):
        if u<=hs_hold:return Lc
        if u<=hs_hold+hit_follow:return Lc+(Lt-Lc)*hseg((u-hs_hold)/hit_follow,0.,.6)
        return Lt+(Le-Lt)*settle((u-hs_hold-hit_follow)/(RECOVER-hs_hold-hit_follow),.9)
    stage_data.append({'action':action,'frames':frames,'cum':cum,'hs':hs,'rel_src':rel/FPS,'turn_src':turn/FPS,
        'ell':ell,'ell_hit':ell_hit,'turn_new':turn_new,'v_contact':v_contact,'dt_follow':dt_follow,
        'L':(La,Lc,Lt,Le)})

def pose_at(stage,src_t):
    return sample(SOURCES[stage],src_t)

# Momentum carry (rigid; every bone the same transform, like V4's carry).
def carry_value(stage,t,hit):
    if not hit:
        tn=stage_data[stage]['turn_new']
        return hermite([(CONTACT-.10,0.,0.),(CONTACT,.30,5.),(CONTACT+.15,1.,0.),(max(tn,CONTACT+.15)+.30,.40,-1.8),(1.58,0.,0.)],t)
    h=STAGE[stage]['hit_stop']
    # Hard impact: the rig shudders against the target through the hit stop,
    # then a short rebound recoil before the heavy return.
    shudder=.07*math.sin(2*math.pi*26.*t)*math.exp(-t/.045) if t<h else 0.
    return hermite([(0.,.30,0.),(h,.30,0.),(h+.09,STAGE[stage]['recoil'],0.),(.55,0.,0.),(RECOVER,0.,0.)],t)+shudder
def carry(pose,stage,g):
    yaw,roll,pitch=STAGE[stage]['carry']
    q=Quaternion((0,0,1),math.radians(yaw*g))@Quaternion((0,1,0),math.radians(roll*g))@Quaternion((1,0,0),math.radians(pitch*g))
    shift=Vector((0.,.012*g,-.008*abs(g)))
    d=Matrix.Translation(CARRY_PIVOT+shift)@q.to_matrix().to_4x4()@Matrix.Translation(-CARRY_PIVOT)
    return {n:d@m for n,m in pose.items()}

FINGERS=('thumb','index','middle','ring','pinky')
explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
def finalize(ref,pose,loosen):
    done=set(explicit)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n]
        if p is None:pose[n]=ref[n].copy();done.add(n);return pose[n]
        local=ref[p].inverted()@ref[n]
        if loosen>0. and n.startswith(FINGERS) and 'metacarpal' not in n:
            v,q,sc=local.decompose();local=Matrix.LocRotScale(v,q.slerp(local_rest[n].to_quaternion(),loosen),sc)
        pose[n]=resolve(p)@local;done.add(n);return pose[n]
    for n in pose:resolve(n)
    for s in 'lr':
        n='ik_hand_'+s
        if n in pose:pose[n]=pose['hand_'+s]@idle['hand_'+s].inverted()@idle[n]
    return pose

def lag_axis(stage):
    sd=stage_data[stage];a=pose_at(stage,sd['rel_src'])['WPN_root'].to_quaternion();c=pose_at(stage,CONTACT)['WPN_root'].to_quaternion()
    d=c@a.inverted();axis,angle=d.to_axis_angle();return axis.normalized() if angle<=math.pi else -axis.normalized()
def contact_spin(stage):
    """World angular velocity of the hammer arriving at contact."""
    sd=stage_data[stage];dt=1/FPS
    a=carry(pose_at(stage,inverse(sd['cum'],sd['ell'](CONTACT-dt))),stage,carry_value(stage,CONTACT-dt,False))['WPN_root'].to_quaternion()
    b=carry(pose_at(stage,CONTACT),stage,carry_value(stage,CONTACT,False))['WPN_root'].to_quaternion()
    axis,angle=(b@a.inverted()).to_axis_angle()
    if angle>math.pi:angle=2*math.pi-angle;axis=-axis
    return axis.normalized(),angle/dt
for stage in range(3):
    sd=stage_data[stage];sd['lag_axis']=lag_axis(stage)
    axis,omega=contact_spin(stage);cap=math.radians(STAGE[stage]['over'])
    # The miss keeps the contact spin and brakes to rest over D (cubic ease-out
    # with matched start speed); the arms swing on about the shoulders.
    D=min(.14,max(.06,3*cap/omega));sd['over_D']=D;sd['over_angle']=min(cap,omega*D/3)
    sd['spin_axis']=axis;sd['contact_spin_deg_s']=math.degrees(omega);sd['turn_new']=CONTACT+D
def overshoot(stage,t):
    sd=stage_data[stage];D=sd['over_D']
    if t<=CONTACT:return 0.
    if t<=CONTACT+D:return sd['over_angle']*(1-(1-(t-CONTACT)/D)**3)
    return sd['over_angle']*(1-settle((t-CONTACT-D)/OVER_RETURN,.8))

def wrist_vs(p,r,s):
    f0=(r['hand_'+s].translation-r['lowerarm_'+s].translation).normalized();f=(p['hand_'+s].translation-p['lowerarm_'+s].translation).normalized()
    dq=p['hand_'+s].to_quaternion()@r['hand_'+s].to_quaternion().inverted();return math.degrees((dq@f0).angle(f))
def build_swing(stage):
    sd=stage_data[stage];prm=STAGE[stage];apex=prm['apex'];out=[];src_times=[]
    m={'lag_bend':0.,'over_bend':0.,'over_shoulder_cm':0.,'over_hand_travel_cm':0.}
    roll_state.clear()
    for i in range(round(SWING*FPS)+1):
        t=i/FPS;src=inverse(sd['cum'],sd['ell'](t));src_times.append(src)
        base=carry(pose_at(stage,src),stage,carry_value(stage,t,False))
        # Grip relaxes into the tension beat and clamps shut for the release.
        h0=prm['hold_start'];loosen=.10*math.sin(math.pi*sat((t-(h0-.08))/(apex-h0+.10)))**2
        u=(t-apex)/(CONTACT-apex)
        phi=math.radians(prm['lag'])*math.sin(math.pi*sat(u))**2*(1-sat(u))**.3 if 0.<u<1. else 0.
        theta=overshoot(stage,t)
        pose=copy.deepcopy(base);R=None
        if phi>1e-5:
            w=base['WPN_root'];pivot=w@PIVOT_LOCAL
            R=Matrix.Translation(pivot)@Quaternion(sd['lag_axis'],-phi).to_matrix().to_4x4()@Matrix.Translation(-pivot)
        elif theta>1e-5:
            pivot=(base['clavicle_l'].translation+base['clavicle_r'].translation)*.5
            R=Matrix.Translation(pivot)@Quaternion(sd['spin_axis'],theta).to_matrix().to_4x4()@Matrix.Translation(-pivot)
        if R is not None:
            pose['WPN_root']=R@base['WPN_root']
            for s in 'lr':solve_arm(pose,base,R@base['hand_'+s],s,rigid_guide=phi<=1e-5)
        out.append(finalize(base,pose,loosen))
        if R is not None:
            for s in 'lr':
                b=wrist_vs(out[-1],base,s)
                if phi>1e-5:m['lag_bend']=max(m['lag_bend'],b)
                else:
                    m['over_bend']=max(m['over_bend'],b)
                    m['over_shoulder_cm']=max(m['over_shoulder_cm'],(out[-1]['clavicle_'+s].translation-base['clavicle_'+s].translation).length*100)
                    m['over_hand_travel_cm']=max(m['over_hand_travel_cm'],(out[-1]['hand_'+s].translation-base['hand_'+s].translation).length*100)
    out[0]=copy.deepcopy(idle);out[-1]=copy.deepcopy(idle)
    return out,src_times,m
def build_recover(stage,contact_pose):
    sd=stage_data[stage];out=[];src_times=[]
    for i in range(round(RECOVER*FPS)+1):
        u=i/FPS;src=inverse(sd['cum'],sd['ell_hit'](u)) if u>STAGE[stage]['hit_stop'] else CONTACT
        src_times.append(src)
        base=carry(pose_at(stage,src),stage,carry_value(stage,u,True))
        out.append(finalize(base,copy.deepcopy(base),0.))
    out[0]=copy.deepcopy(contact_pose);out[-1]=copy.deepcopy(idle)
    return out,src_times

def new_time_of_src(src_times,src):
    for i,s in enumerate(src_times):
        if s>=src-1e-6:return i/FPS
    return SWING

JOINTS=('clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r')
def head_speeds(seq):return [((b['WPN_root']@HEAD)-(a['WPN_root']@HEAD)).length*FPS for a,b in zip(seq,seq[1:])]
def holds(sp,start=.20,end=None):
    end=end or len(sp)/FPS-.12;res=[];s0=None
    for i,v in enumerate(sp):
        t=i/FPS
        if start<=t<=end and v<.25:
            s0=i if s0 is None else s0
        elif s0 is not None:
            if i-s0>=12:res.append([round(s0/FPS,3),round(i/FPS,3)])
            s0=None
    return res
results={};clips={};timing={'hold':[],'apex':[],'turn':[],'chain':[],'hit_chain':[],'whoosh':[],'hit_stop':[]}
for stage in range(3):
    swing,src_times,layer=build_swing(stage)
    recover,rsrc=build_recover(stage,swing[round(CONTACT*FPS)])
    sd=stage_data[stage];prm=STAGE[stage]
    # Stage 2 hands are back on the right-top grip only after V5's swap back.
    swap_back_src=1.40 if stage==1 else sd['turn_src']
    chain=max(sd['turn_new']+.02,new_time_of_src(src_times,swap_back_src))
    hit_chain=prm['hit_stop']+.16+.02
    if stage==1:
        hit_chain=max(hit_chain,next((i/FPS for i,s in enumerate(rsrc) if i/FPS>prm['hit_stop'] and s>=1.40),RECOVER*.7))
    timing['hold'].append(prm['hold_start'])
    timing['apex'].append(prm['apex']);timing['turn'].append(round(sd['turn_new'],4));timing['chain'].append(round(chain,4))
    timing['hit_chain'].append(round(hit_chain,4));timing['whoosh'].append(round(CONTACT-prm['whoosh_lead'],4));timing['hit_stop'].append(prm['hit_stop'])
    sp=head_speeds(swing);old=sd['hs']
    steps=max((b[n].translation-a[n].translation).length*100 for a,b in zip(swing,swing[1:]) for n in JOINTS)
    rsteps=max((b[n].translation-a[n].translation).length*100 for a,b in zip(recover,recover[1:]) for n in JOINTS)
    bone=max(abs((p[b+'_'+s].translation-p[a+'_'+s].translation).length-(rest[b+'_'+s].translation-rest[a+'_'+s].translation).length)*1000
        for p in swing+recover for s in 'lr' for a,b in [('upperarm','lowerarm'),('lowerarm','hand')])
    carry_shoulder=max((p['clavicle_'+s].translation-q['clavicle_'+s].translation).length*100
        for p,t in zip(swing,[i/FPS for i in range(len(swing))]) for q in [pose_at(stage,src_times[round(t*FPS)])] for s in 'lr')
    peak=max(range(len(sp)),key=lambda i:sp[i])
    results[SOURCES[stage]]={
        'source_release_start':sd['rel_src'],'source_turn':sd['turn_src'],'new_apex':prm['apex'],'new_turn':round(sd['turn_new'],4),
        'release_seconds':round(CONTACT-prm['apex'],3),'contact_spin_deg_s':round(sd['contact_spin_deg_s'],1),
        'miss_overshoot_deg':round(math.degrees(sd['over_angle']),2),'miss_brake_seconds':round(sd['over_D'],4),
        'head_speed_peak_m_s':[round(sp[peak],2),round(peak/FPS,3)],'old_head_speed_peak_m_s':round(max(old),2),
        'head_speed_at':{f'{t:.3f}':round(sp[min(len(sp)-1,round(t*FPS))],2) for t in
            (.1,.3,.5,prm['hold_start']-.05,prm['hold_start']+.02,prm['apex']-.01,prm['apex']+.03,prm['apex']+.06,CONTACT-.03,CONTACT-.01,CONTACT,1.,1.03,1.1,1.2,1.4,1.6)},
        'hold_start':prm['hold_start'],'hold_seconds':prm['hold'],
        'holds_over_40ms':holds(sp),'old_holds_over_40ms':holds(old[1:]),
        'max_joint_step_cm':round(steps,3),'recover_max_joint_step_cm':round(rsteps,3),'bone_length_error_mm':bone,
        'lag_extra_wrist_bend_deg':round(layer['lag_bend'],2),'overshoot_extra_wrist_bend_deg':round(layer['over_bend'],2),
        'overshoot_shoulder_support_cm':round(layer['over_shoulder_cm'],2),'overshoot_hand_travel_cm':round(layer['over_hand_travel_cm'],2),
        'carry_and_support_max_shoulder_shift_cm':round(carry_shoulder,2),
        'arm_reach_ratio_max':{s:round(max(((p['hand_'+s].translation-p['upperarm_'+s].translation).length/
            ((p['lowerarm_'+s].translation-p['upperarm_'+s].translation).length+(p['hand_'+s].translation-p['lowerarm_'+s].translation).length)) for p in swing),4) for s in 'lr'},
        'chain_clip':round(chain,4),'hit_chain_clip':round(hit_chain,4),
        'recover_frame0_is_contact':max((recover[0][n].translation-swing[round(CONTACT*FPS)][n].translation).length for n in JOINTS)<1e-6}
    clips[SOURCES[stage]]=swing;clips[SOURCES[stage]+'Recover']=recover
print('WARHAMMER_FLOW_PLAN '+json.dumps({'results':results,'timing':timing}))
(P/'plan.json').write_text(json.dumps({'results':results,'timing':timing,'stage_params':STAGE},indent=1),encoding='utf-8')
if PLAN:raise SystemExit(0)

def arr(v):return '{'+','.join(f'{x:.4f}f' for x in v)+'}'
header=f'''#pragma once
#include "CoreMinimal.h"
// Generated by SourceAssets/SteelWarhammer20261014/NormalComboRhythmV7/author_rhythm.py.
// Clip seconds of the V7 normal hammer cuts (contact {CONTACT:.2f}, swing {SWING:.2f}, hit clip {RECOVER:.2f}).
namespace ProductionBluntComboTiming
{{
    inline constexpr float HoldClip[3]={arr(timing['hold'])};      // load reaches its tension beat
    inline constexpr float ApexClip[3]={arr(timing['apex'])};      // explosive release (downswing) begins
    inline constexpr float TurnClip[3]={arr(timing['turn'])};      // miss follow-through turnaround
    inline constexpr float ChainClip[3]={arr(timing['chain'])};    // earliest visual chain point after a miss
    inline constexpr float HitChainClip[3]={arr(timing['hit_chain'])}; // earliest chain point in the hit clip
    inline constexpr float WhooshClip[3]={arr(timing['whoosh'])};  // ordinary swing sound start
    inline constexpr float HitStopClip[3]={arr(timing['hit_stop'])};
}}
'''
(ROOT/'Source/FPSGAME/Production/ProductionBluntComboTiming.h').write_text(header,encoding='utf-8')
for name,poses in clips.items():
    if name in bpy.data.actions:bpy.data.actions[name].name=name+'_Source'
for name,poses in clips.items():bake(name,poses,FPS)
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Combo_Rhythm_Editable.blend'))
receipt={'revision':'NormalComboRhythmV7_20261015','clips':list(clips),'fps':FPS,'runtime_destination':'/Game/Weapons/SteelWarhammer20261014/NormalComboV4',
 'rhythm':'load -> tension beat (slow drift) -> explosive power-curve release -> hard impact (shudder/recoil on hit, braked swing-on on miss) -> heavy return',
 'pose_sources':{'Slash1/Slash3':str(V4),'Slash2':str(V5)},'joint_policy':'Accepted poses retimed by motion arc length; rigid carry; release lag solved with native lengths',
 'contact_seconds':CONTACT,'swing_seconds':SWING,'hit_recover_seconds':RECOVER,'stage_params':STAGE,'timing':timing,'results':results,'runtime_tested':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_FLOW_AUTHORED')
