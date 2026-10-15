"""Warhammer normal combo stage 2 with a hand swap (left hand leads on top).

Diagnosis (Diagnosis/probe.json): the old stage 2 kept the right-hand-top grip
and loaded over the LEFT shoulder, so the right arm crossed over the head (its
elbow above eye level at the load) and stayed chicken-winged through contact.

New stage 2:
- Strike: the accepted stage 1 (right-to-left, right hand top) mirrored left/
  right, so the left hand leads on top and the cut runs upper-left to lower-
  right with the same joints, timing, contact and carry as stage 1.
- Wind-up hand swap while the hammer rises from the common idle: the top right
  hand slides down to the left hand, the left hand lets go, passes over it and
  takes the top position, then the right hand slides to the bottom.
- Recovery hand swap back to the common idle (right hand top) in mirror order,
  so stage 3, idle and every other action keep their right-top start.
Holding hands keep a real shaft relation (sliding = cylindrical interpolation
about the measured shaft axis); arms use native lengths, solved from blended
accepted references (old stage 2 for the right-top idle side, mirrored stage 1
for the left-top side). Contact 0.97 s / 1.75 s swing / 0.80 s hit recovery.
"""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
PLAN='--plan' in sys.argv
FPS=300;SWING=1.75;CONTACT=.97;RECOVER=.80
SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindInertiaV8/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'sat','smooth','rigid','frame','axial'}],type_ignores=[]),'<native_grip_support>','exec'))
roll_state={}
def solve_arm(out,ref,target,side):
    """WhirlwindInertiaV8 full-chain solver; the elbow guide is the reference
    elbow carried by the wrist correction's translation only, so a large palm
    turn about the shaft cannot swing the guide across the elbow circle."""
    U,L,H,C=[x+'_'+side for x in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[ref[n].translation for n in (U,L,H)];u0,l0=e0-s0,h0-e0
    normal=u0.cross(l0).normalized();d=target@ref[H].inverted();dq=d.to_quaternion()
    h=target.translation;ideal_e=e0+(h-h0)
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
    rig.animation_data.action=bpy.data.actions[action];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    f=max(0.,min(SWING,t))*FPS;scene.frame_set(int(f),subframe=f-int(f))
    return {b.name:b.matrix.copy() for b in rig.pose.bones}
idle=sample('A_Warhammer_Slash1',0.)

# Left/right mirror of the accepted stage 1 -----------------------------------
MX=Matrix.Diagonal((-1,1,1,1));SY=Matrix.Diagonal((1,-1,1,1))
def partner(n):return n[:-2]+'_r' if n.endswith('_l') else n[:-2]+'_l' if n.endswith('_r') else n
ARM_PREFIX=('clavicle','upperarm','lowerarm','hand_','thumb','index','middle','ring','pinky')
arm_bones=[n for n in rest if n.startswith(ARM_PREFIX) and n[-2:] in ('_l','_r')]
arm_asymmetry_mm=max((rest[n].translation-MX@rest[partner(n)].translation).length for n in arm_bones)*1000
if arm_asymmetry_mm>1.:raise RuntimeError('Arm rest pose is not left/right symmetric: %.3f mm'%arm_asymmetry_mm)
fix={n:rest[partner(n)].inverted()@MX@rest[n] for n in rest}
def mirror_pose(pose):
    # Hammer: reflect the frame and its local Y, keeping shaft (Z) and head (X).
    return {n:(MX@pose[n]@SY if n=='WPN_root' else MX@pose[partner(n)]@fix[n]) for n in pose}
cache={}
def A(t):
    k=('A',round(t*FPS*8))
    if k not in cache:cache[k]=sample('A_Warhammer_Slash2',t)
    return cache[k]
def B(t):
    k=('B',round(t*FPS*8))
    if k not in cache:cache[k]=mirror_pose(sample('A_Warhammer_Slash1',t))
    return cache[k]

# Shaft geometry (measured centreline, as InspectV1) -------------------------
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
hammer_local=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
band=[p for p in hammer_local if -.08<=p.z<=.38]
CX=(min(p.x for p in band)+max(p.x for p in band))*.5;CY=(min(p.y for p in band)+max(p.y for p in band))*.5
grip_idle={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
Z_BOTTOM=grip_idle['l'].translation.z;Z_TOP=grip_idle['r'].translation.z
Z_MEET=Z_BOTTOM+.095   # sliding hand stops one palm width above the lower hand
pivot_local=Vector((CX,CY,(Z_BOTTOM+Z_TOP)*.5))
LIFT=.085              # free hand clears the other hand while passing it

def cyl(g):
    p=g.translation;return p.z,math.atan2(p.y-CY,p.x-CX),math.hypot(p.x-CX,p.y-CY),g.to_quaternion()
def from_cyl(z,a,r,q):return rigid(Vector((CX+r*math.cos(a),CY+r*math.sin(a),z)),q)
def slide(g0,g1,u,z=None,lift=0.):
    """Palm moves around/along the round shaft; z may be keyed separately."""
    z0,a0,r0,q0=cyl(g0);z1,a1,r1,q1=cyl(g1);u=sat(u)
    da=(a1-a0+math.pi)%(2*math.pi)-math.pi
    zz=z0+(z1-z0)*u if z is None else z
    return from_cyl(zz,a0+da*u,r0+(r1-r0)*u+lift,q0.slerp(q1,u))
def blend_frame(a,b,w):
    q=a.to_quaternion().slerp(b.to_quaternion(),w);p=(a@pivot_local).lerp(b@pivot_local,w)
    return rigid(p-q@pivot_local,q)

# Swap schedules -------------------------------------------------------------
# Wind-up: the old right-top raise (A) slows onto its near-sagittal vertical
# frame; there the right-top hold and its exact mirror (C) hold the same
# hammer, so the swap happens upright: R (top) slides down to meet L, L lets
# go, passes over R to the top, R slides on to the bottom. The left-top hold
# then tips back into the mirrored stage-1 load (B).
# Recovery: at the forward follow-through, where A and B share the same hammer
# axis, the order mirrors (L slides down, R passes over to the top), then A's
# right-top return reaches the common idle.
T_V0,T_V1,TA_V=.28,.58,.40
WIND={'meet':(.28,.37),'free':(.34,.53),'settle':(.50,.58)}
T_L0,T_L1,TB_L0,TB_L1=.58,.82,.64,.82
T_B0,T_B1=1.12,1.40
BACK={'meet':(1.12,1.20),'free':(1.17,1.35),'settle':(1.32,1.40)}
def prog(t,span):return smooth((t-span[0])/(span[1]-span[0]))
def C(t):
    k=('C',round(t*FPS*8))
    if k not in cache:cache[k]=mirror_pose(A(t))
    return cache[k]
def warp_a(t):
    """A clock through the upright swap: leaves at A's speed, settles on TA_V."""
    if t<=T_V0:return t
    u=sat((t-T_V0)/(T_V1-T_V0));s=(T_V1-T_V0)/(TA_V-T_V0)
    return T_V0+(TA_V-T_V0)*((u**3-2*u*u+u)*s+(-2*u**3+3*u*u))
def relation(pose,side):return pose['WPN_root'].inverted()@pose['hand_'+side]
def swap_grip(src,dst,s,t,slider,side):
    meet=prog(t,s['meet']);settle=prog(t,s['settle']);passing=prog(t,s['free'])
    g0=relation(src,side);g1=relation(dst,side)
    if side==slider:
        z0=cyl(g0)[0];z1=cyl(g1)[0];z=z0+(Z_MEET-z0)*meet+(z1-Z_MEET)*settle
        return slide(g0,g1,(meet+settle)*.5,z=z),(meet+settle)*.5
    return slide(g0,g1,passing,lift=LIFT*math.sin(math.pi*sat(passing))),passing
def exact(p):return p['WPN_root'],p,p,{'l':0.,'r':0.},0.,{s:relation(p,s) for s in 'lr'}
def phase(t):
    """(weapon frame, source pose, target pose, per-arm role weights, body weight, grips)."""
    if t<=T_V0:return exact(A(t))
    if t<=T_V1:
        ta=warp_a(t);pa=A(ta);pc=C(ta);w=smooth((t-T_V0)/(T_V1-T_V0));grips={};k={}
        for s in 'lr':grips[s],k[s]=swap_grip(pa,pc,WIND,t,'r',s)
        return blend_frame(pa['WPN_root'],pc['WPN_root'],w),pa,pc,k,w,grips
    if t<=T_L1:
        u=(t-T_L0)/(T_L1-T_L0);w=smooth(u);pc=C(TA_V);pb=B(TB_L0+(TB_L1-TB_L0)*u)
        return blend_frame(pc['WPN_root'],pb['WPN_root'],w),pc,pb,{'l':w,'r':w},w,{s:slide(relation(pc,s),relation(pb,s),w) for s in 'lr'}
    if t<=T_B0:return exact(B(t))
    if t<=T_B1:
        pb=B(T_B0);pa=A(t);w=smooth((t-T_B0)/(T_B1-T_B0));grips={};k={}
        for s in 'lr':grips[s],k[s]=swap_grip(pb,pa,BACK,t,'l',s)
        return blend_frame(pb['WPN_root'],pa['WPN_root'],w),pb,pa,k,w,grips
    return exact(A(t))
def family(t):
    """0 = right-top hold (old stage 2 / idle), 1 = left-top hold (mirrored stage 1)."""
    if t<=T_V0 or t>=T_B1:return 0.
    if t<=T_V1:return smooth((t-T_V0)/(T_V1-T_V0))
    if t<=T_B0:return 1.
    return 1-smooth((t-T_B0)/(T_B1-T_B0))

ARM_CHAIN={s:[n for n in arm_bones if n.endswith('_'+s)] for s in ('l','r')}
SIDE_OF={n:s for s in 'lr' for n in ARM_CHAIN[s]}
ORDER=[];_seen=set()
def _visit(n):
    if n in _seen:return
    if parents[n]:_visit(parents[n])
    _seen.add(n);ORDER.append(n)
for _n in rest:_visit(_n)
def pose_blend(pa,pb,weights,body_weight):
    """Parent-space blend of the whole reference: each arm by its own hand role
    weight, the body/carry chain by the hammer-family weight (native lengths)."""
    out={}
    for n in ORDER:
        p=parents[n];w=weights[SIDE_OF[n]] if n in SIDE_OF else body_weight
        if p is None:
            av,aq,sc=pa[n].decompose();bv,bq,_=pb[n].decompose();out[n]=Matrix.LocRotScale(av.lerp(bv,w),aq.slerp(bq,w),sc);continue
        la=pa[p].inverted()@pa[n];lb=pb[p].inverted()@pb[n]
        av,aq,sc=la.decompose();bv,bq,_=lb.decompose();v=av.lerp(bv,w)
        # Upper arm, forearm and wrist offsets are native segment lengths; the
        # clavicle offset is animated (arm-root clearance) and is interpolated.
        if n.startswith(('upperarm','lowerarm','hand_')) and v.length>1e-8:v=v.normalized()*av.length
        out[n]=out[p]@Matrix.LocRotScale(v,aq.slerp(bq,w),sc)
    return out

FINGERS=('thumb','index','middle','ring','pinky')
def finger_open(side,t):
    s=WIND if t<1. else BACK;free='l' if t<1. else 'r'
    if side==free:
        a,b=s['free'];return .80*smooth((t-(a-.03))/.05)*(1-smooth((t-(b-.035))/.05))
    a,b=s['meet'][0],s['settle'][1];return .18*smooth((t-a)/.04)*(1-smooth((t-(b-.03))/.04))

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
if '--debug' in sys.argv:
    pb=B(.82);pc=C(TA_V)
    self_rebuild=pose_blend(pb,pb,{'l':1.,'r':1.},1.)
    full=pose_blend(pc,pb,{'l':1.,'r':1.},1.)
    worst=lambda a,b:max(((a[n].translation-b[n].translation).length,n) for n in a)
    print('DEBUG self',worst(self_rebuild,pb),'full',worst(full,pb))
    for n in ('VM_Root','root','pelvis','spine_05','clavicle_r','upperarm_r','hand_r'):
        print('DEBUG',n,parents[n],(full[n].translation-pb[n].translation).length,(pc[n].translation-pb[n].translation).length)
    raise SystemExit(0)
last_ref={}
def build_pose(t):
    w,pa,pb,k,body,grips=phase(t)
    ref=pa if pa is pb else pose_blend(pa,pb,k,body)
    last_ref['pose']=ref
    pose=copy.deepcopy(ref);pose['WPN_root']=w
    free,passing=('l',prog(t,WIND['free'])) if T_V0<t<T_V1 else ('r',prog(t,BACK['free'])) if T_B0<t<T_B1 else (None,0.)
    for side in ('l','r'):
        target=w@grips[side]
        if side==free:
            # The released palm travels the lifted path around the shaft; in the
            # air it keeps the arm's own wrist line and turns into the exact
            # grip orientation as it closes on the shaft.
            g=1-.75*math.sin(math.pi*sat(passing))
            target=rigid(target.translation,ref['hand_'+side].to_quaternion().slerp(target.to_quaternion(),g))
        solve_arm(pose,ref,target,side)
    done=set(explicit)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n]
        if p is None:pose[n]=ref[n].copy();done.add(n);return pose[n]
        local=ref[p].inverted()@ref[n]
        if n.startswith(FINGERS) and 'metacarpal' not in n:
            amount=finger_open(n[-1],t)
            if amount>0.:
                v,q,sc=local.decompose();local=Matrix.LocRotScale(v,q.slerp(local_rest[n].to_quaternion(),amount),sc)
        pose[n]=resolve(p)@local;done.add(n);return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    return pose

# Hit recovery reuses this swing after contact, on the V4 recovery clock.
RECOVER_KEYS=[(0.,CONTACT),(.07,CONTACT),(.20,1.10),(.38,1.30),(RECOVER,SWING)]
def recover_time(u):
    for (a,ta),(b,tb) in zip(RECOVER_KEYS,RECOVER_KEYS[1:]):
        if u<=b:return ta+(tb-ta)*(u-a)/(b-a) if b>a else ta
    return SWING

swing_times=[i/FPS for i in range(round(SWING*FPS)+1)]
def wrist_bend(p,r,s):
    f0=(r['hand_'+s].translation-r['lowerarm_'+s].translation).normalized();f=(p['hand_'+s].translation-p['lowerarm_'+s].translation).normalized()
    d=p['hand_'+s].to_quaternion()@r['hand_'+s].to_quaternion().inverted();return math.degrees((d@f0).angle(f))
swing=[];twist={'l':[],'r':[]};vs_ref=[]
for t in swing_times:
    swing.append(build_pose(t));r=last_ref['pose']
    for s in ('l','r'):twist[s].append(math.degrees(roll_state.get(s,0.)))
    vs_ref.append({'t':round(t,4),'bend':{s:round(wrist_bend(swing[-1],r,s),1) for s in 'lr'},
        'shoulder_cm':{s:round((swing[-1]['clavicle_'+s].translation-r['clavicle_'+s].translation).length*100,2) for s in 'lr'},
        'hand_correction_cm':{s:round((swing[-1]['hand_'+s].translation-r['hand_'+s].translation).length*100,2) for s in 'lr'},
        'elbow':{s:[round(x,4) for x in swing[-1]['lowerarm_'+s].translation] for s in 'lr'},
        'ref_elbow':{s:[round(x,4) for x in r['lowerarm_'+s].translation] for s in 'lr'},
        'hand':{s:[round(x,4) for x in swing[-1]['hand_'+s].translation] for s in 'lr'},
        'ref_hand':{s:[round(x,4) for x in r['hand_'+s].translation] for s in 'lr'}})
swing[0]=copy.deepcopy(idle);swing[-1]=copy.deepcopy(idle)
roll_state.clear()
recover_times=[recover_time(i/FPS) for i in range(round(RECOVER*FPS)+1)]
recover=[build_pose(t) for t in recover_times];recover[-1]=copy.deepcopy(idle)

# Measurements (authoring, not acceptance) ------------------------------------
def gz(p,s):return round((p['WPN_root'].inverted()@p['hand_'+s]).translation.z,4)
def bend(p,r,s):
    f0=(r['hand_'+s].translation-r['lowerarm_'+s].translation).normalized();f=(p['hand_'+s].translation-p['lowerarm_'+s].translation).normalized()
    d=p['hand_'+s].to_quaternion()@r['hand_'+s].to_quaternion().inverted();return math.degrees((d@f0).angle(f))
JOINTS=('clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r')
def steps(seq,times):
    return sorted(((b[n].translation-a[n].translation).length*100,round(times[i+1],3),n) for i,(a,b) in enumerate(zip(seq,seq[1:])) for n in JOINTS)[-5:]
def turn(a,b):
    x=math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle);return min(x,360-x)
def angle_steps(seq,times):
    return sorted((turn(a[n],b[n]),round(times[i+1],3),n)
        for i,(a,b) in enumerate(zip(seq,seq[1:])) for n in ('lowerarm_l','lowerarm_r','upperarm_l','upperarm_r','hand_l','hand_r'))[-5:]
strike=[i for i,t in enumerate(swing_times) if T_L1<=t<=T_B0]
strike_dev=max((swing[i]['hand_'+s].translation-B(swing_times[i])['hand_'+s].translation).length for i in strike for s in ('l','r'))*1000
bone_error=max(abs((p[b+'_'+s].translation-p[a+'_'+s].translation).length-(rest[b+'_'+s].translation-rest[a+'_'+s].translation).length)*1000
    for p in swing+recover for s in ('l','r') for a,b in [('upperarm','lowerarm'),('lowerarm','hand')])
hand_gap=min((p['hand_l'].translation-p['hand_r'].translation).length for p in swing)
clav=max((p['clavicle_'+s].translation-idle['clavicle_'+s].translation).length for p in swing+recover for s in ('l','r'))*100
def reach(p,s):
    a,e,h=[p[n+'_'+s].translation for n in ('upperarm','lowerarm','hand')];return (h-a).length/((e-a).length+(h-e).length)
reach_max={s:round(max(reach(p,s) for p in swing+recover),4) for s in 'lr'}
source_b=[B(t) for t in swing_times]
b_steps=max((b[n].translation-a[n].translation).length*100 for i,(a,b) in enumerate(zip(source_b,source_b[1:])) if T_L1<=swing_times[i]<=T_B0 for n in JOINTS)
jumps=[(round(swing_times[i+1],4),n,round((b[n].translation-a[n].translation).length*100,2)) for i,(a,b) in enumerate(zip(swing,swing[1:]))
    for n in JOINTS if not (T_L1<=swing_times[i]<=T_B0) and (b[n].translation-a[n].translation).length>.03]
worst={k:max(((r[k][s],r['t'],s) for r in vs_ref for s in 'lr')) for k in ('bend','shoulder_cm','hand_correction_cm')}
KEYS=[0.,.20,.30,.36,.42,.47,.54,.62,.70,.82,.97,1.10,1.16,1.22,1.28,1.34,1.38,1.50,1.62,1.75]
table=[]
for t in KEYS:
    i=round(t*FPS);p=swing[i];ref=A(t) if family(t)<.5 else B(min(t,T_B0))
    table.append({'t':t,'grip_z':{s:gz(p,s) for s in ('l','r')},'family':round(family(t),3),
        'elbow':{s:[round(x,3) for x in p['lowerarm_'+s].translation] for s in ('l','r')},
        'wrist_bend_vs_family_ref':{s:round(bend(p,ref,s),1) for s in ('l','r')},'forearm_twist':{s:round(twist[s][i],1) for s in ('l','r')}})
metrics={'arm_rest_asymmetry_mm':arm_asymmetry_mm,'strike_matches_mirrored_stage1_mm':strike_dev,'max_bone_length_error_mm':bone_error,
 'largest_joint_steps_cm':[[round(a,3),b,c] for a,b,c in steps(swing,swing_times)],
 'largest_joint_turns_deg':[[round(a,2),b,c] for a,b,c in angle_steps(swing,swing_times)],
 'recover_largest_joint_steps_cm':[[round(a,3),b,c] for a,b,c in steps(recover,[i/FPS for i in range(len(recover))])],
 'min_hand_distance_m':round(hand_gap,4),'max_clavicle_shift_cm':round(clav,3),'arm_reach_ratio_max':reach_max,
 'strike_source_max_step_cm':round(b_steps,3),'steps_over_3cm_outside_strike':jumps[:40],'worst_vs_reference':worst,
 'forearm_twist_range':{s:[round(min(v),1),round(max(v),1)] for s,v in twist.items()},
 'recover_frame0_equals_contact':max((recover[0][n].translation-swing[round(CONTACT*FPS)][n].translation).length for n in JOINTS)<1e-6,
 'keys':table}
print('WARHAMMER_SWAP_PLAN '+json.dumps({k:v for k,v in metrics.items() if k!='keys'}))
(P/'plan.json').write_text(json.dumps(metrics,indent=1),encoding='utf-8')
(P/'plan_frames.json').write_text(json.dumps(vs_ref),encoding='utf-8')
if PLAN:raise SystemExit(0)

bake('A_Warhammer_Slash2',swing,FPS);bake('A_Warhammer_Slash2Recover',recover,FPS)
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash2'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Combo_Swap_Editable.blend'))
receipt={'revision':'NormalComboSwapV5_20261015','clips':['A_Warhammer_Slash2','A_Warhammer_Slash2Recover'],'fps':FPS,
 'runtime_destination':'/Game/Weapons/SteelWarhammer20261014/NormalComboV4','source':str(SOURCE),
 'strike':'Accepted A_Warhammer_Slash1 mirrored left/right (left hand top), V4 timing/carry; hammer frame reflected with local Y',
 'right_top_reference':'Old A_Warhammer_Slash2 (idle side of the swaps only)','swing_seconds':SWING,'contact_seconds':CONTACT,
 'hit_recover_seconds':RECOVER,'hit_recover_clock':RECOVER_KEYS,'windup_swap_seconds':WIND,'recovery_swap_seconds':BACK,
 'phases':{'right_top_raise':[0.,T_V0],'upright_swap':[T_V0,T_V1],'upright_frame_of_old_stage2':TA_V,'tip_back_to_mirrored_load':[T_L0,T_L1],
     'mirrored_stage1_load_strike_follow':[T_L1,T_B0],'forward_swap_back':[T_B0,T_B1],'old_stage2_return_to_idle':[T_B1,SWING]},
 'grip_z_m':{'bottom':Z_BOTTOM,'top':Z_TOP,'meet':Z_MEET},'free_hand_lift_m':LIFT,'shaft_axis_point_local_m':[CX,CY],
 'metrics':metrics,'runtime_tested':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_SWAP_AUTHORED')
