"""Author a native two-hand butt strike from _5pAl232f38, 55.65-56.95.

The saved V9-compatible grip is authoritative. Both hands remain attached;
native bone lengths, hinge planes and the 100/50 forearm stations are retained.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
FPS=120
DURATION=1.3
NATIVE=json.loads((P/'native-idle.json').read_text())
INPUT=json.loads((P/'native-author-inputs.json').read_text())
parents=INPUT['parents']
C=Matrix.Diagonal(Vector((1,-1,1)))
def mat(p,q,s=(1,1,1)):return Matrix.LocRotScale(Vector(p),q,Vector(s))
idle={n:mat(k['p'],Quaternion(k['q']),k['s']) for n,k in INPUT['world'].items()}
mesh_bind=json.loads((P/'Review/current-mesh.json').read_text())['bones']
bind={n:mat(C@Vector(k['p'])*.01,(C@Quaternion(k['q']).to_matrix()@C).to_quaternion(),k['s']) for n,k in mesh_bind.items()}
local={n:idle[p].inverted()@m if p else m.copy() for n,m in idle.items() for p in [parents[n]]}
base=idle['wpn_root'].to_quaternion()
axis0=base@Vector((0,0,1))
grip=base.inverted()@(idle['hand_l'].translation-idle['wpn_root'].translation)

# Left wrist in camera metres (+X right, +Y forward). The middle run traces
# the observed left fist; entry/exit adapt the halberd to the hammer's idle.
keys=[
 (0.,list(idle['hand_l'].translation),list(axis0),0.),
 (.05,[.015,.36,-.22],[.92,-.05,.39],-3.),
 (.10,[.14,.30,-.15],[.95,-.28,.15],-10.),
 (.15,[.205,.32,-.105],[.87,-.49,.01],-20.),
 (.233333333,[.045,.48,-.075],[.78,-.60,-.17],-20.),
 (.283333333,[.06,.47,-.085],[.80,-.57,-.18],-20.),
 (.40,[.155,.40,-.135],[.87,-.46,-.17],-19.),
 (.60,[.17,.33,-.20],[.91,-.39,-.12],-17.),
 (.80,[.065,.28,-.31],[.97,-.24,.03],-12.),
 (.95,[.165,.29,-.28],[.50,.13,.85],-6.),
 (1.10,[.04,.34,-.28],[.78,.12,.61],-2.),
 (1.30,list(idle['hand_l'].translation),list(axis0),0.)]

def tangent(values,i):
    if i==0 or i==len(values)-1:return 0.
    h0=keys[i][0]-keys[i-1][0];h1=keys[i+1][0]-keys[i][0]
    a=(values[i]-values[i-1])/h0;b=(values[i+1]-values[i])/h1
    if a*b<=0:return 0.
    w1=2*h1+h0;w2=h1+2*h0
    return (w1+w2)/(w1/a+w2/b)

def curve(values,t):
    i=next((i for i in range(len(keys)-1) if t<=keys[i+1][0]),len(keys)-2)
    dt=keys[i+1][0]-keys[i][0];u=max(0.,min(1.,(t-keys[i][0])/dt))
    return (2*u**3-3*u*u+1)*values[i]+(u**3-2*u*u+u)*dt*tangent(values,i)+(-2*u**3+3*u*u)*values[i+1]+(u**3-u*u)*dt*tangent(values,i+1)

def weapon(t):
    p=Vector([curve([k[1][j] for k in keys],t) for j in range(3)])
    direction=Vector([curve([k[2][j] for k in keys],t) for j in range(3)]).normalized()
    roll=math.radians(curve([k[3] for k in keys],t))
    q=Quaternion(direction,roll)@axis0.rotation_difference(direction)@base
    return mat(p-q@grip,q,idle['wpn_root'].to_scale())

def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def axial(q,axis):
    v=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (v+math.pi)%(2*math.pi)-math.pi

def arm(side,target,previous):
    U,L,H,CL=[n+'_'+side for n in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[idle[n].translation for n in (U,L,H)]
    u0=e0-s0;l0=h0-e0;h=target.translation
    hand_delta=target.to_quaternion()@bind[H].to_quaternion().inverted()
    neutral=(hand_delta@(bind[H].translation-bind[L].translation)).normalized()
    desired=Vector((.32,.70,.64) if side=='l' else (.38,.65,.66)).normalized()
    pole=desired-neutral*desired.dot(neutral)
    if pole.length<1e-6:pole=neutral.cross(Vector((0,0,1)))
    pole.normalize();best=None;sign=1 if side=='r' else -1
    for bend in range(0,26,5):
      for around in range(-180,180,15):
        radial=Quaternion(neutral,math.radians(around))@pole
        fore=neutral*math.cos(math.radians(bend))+radial*math.sin(math.radians(bend))
        e=h-fore*l0.length
        upper=(e-s0).normalized();shoulder=e-upper*u0.length
        visible=max(0.,shoulder.z+max(0.,shoulder.y)*.80+.075)
        cost=16*(shoulder-s0).length_squared+.18*fore.angle(desired)**2
        cost+=15*max(0.,.075-sign*shoulder.x)**2+80*visible**2
        cost+=8*max(0.,shoulder.y-.09)**2+.015*math.radians(bend)**2
        if previous:cost+=2*(e-previous['e']).length_squared
        if best is None or cost<best['cost']:best=dict(cost=cost,s=shoulder,e=e)
    return best

times=[i/FPS for i in range(round(DURATION*FPS)+1)]
weapons=[weapon(t) for t in times]
targets={s:[w@idle['wpn_root'].inverted()@idle['hand_'+s] for w in weapons] for s in ('l','r')}
solutions={}
for side in ('l','r'):
    raw=[];prev=None
    for target in targets[side]:prev=arm(side,target,prev);raw.append(prev)
    # Smooth the fitted shoulder/elbow guides, then reconstruct exact lengths.
    solutions[side]=[]
    U,L,H=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    s0,e0,h0=[idle[n].translation for n in (U,L,H)];u0=e0-s0;l0=h0-e0
    for i in range(len(raw)):
        ids=range(max(0,i-3),min(len(raw),i+4))
        s=sum((raw[j]['s'] for j in ids),Vector())/len(ids)
        guide=sum((raw[j]['e'] for j in ids),Vector())/len(ids)
        h=targets[side][i].translation
        fore=(h-guide).normalized();e=h-fore*l0.length
        s=e-(e-s).normalized()*u0.length
        solutions[side].append((s,e))


def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(10-15*t+6*t*t)

# Keep elbow hinge roll continuous through the short thrust. Smoothing a
# shoulder position alone let the hinge plane swing across the wrist rapidly.
# Preserve the hand and elbow paths; carry the residual from the shoulder.
for side in ('l','r'):
    U,L,H=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    bu=bind[L].translation-bind[U].translation;bl=bind[H].translation-bind[L].translation
    bn=bu.cross(bl).normalized();raw=[];frames=[]
    for i,(s,e) in enumerate(solutions[side]):
        h=targets[side][i].translation;fore=(h-e).normalized();upper=(e-s).normalized()
        hand_delta=targets[side][i].to_quaternion()@bind[H].to_quaternion().inverted()
        full=(hand_delta@bl).rotation_difference(fore)@hand_delta
        normal=(full@bn).normalized();plane=upper.cross(fore).normalized()
        angle=math.atan2(fore.dot(normal.cross(plane)),normal.dot(plane))
        if raw:angle=raw[-1]+(angle-raw[-1]+math.pi)%(2*math.pi)-math.pi
        raw.append(angle);frames.append((fore,normal,upper.angle(fore),(e-s).length))
    for i,(fore,normal,flex,length) in enumerate(frames):
        ids=range(max(0,i-18),min(len(raw),i+19));ws=[math.exp(-.5*((j-i)/7.)**2) for j in ids]
        roll=sum(raw[j]*w for j,w in zip(ids,ws))/sum(ws)
        plane=Quaternion(fore,roll)@normal
        upper=Quaternion(plane,-flex)@fore;s,e=solutions[side][i]
        solutions[side][i]=(e-upper*length,e)

poses=[];rolls={}
for i,t in enumerate(times):
    pose={n:m.copy() for n,m in idle.items()};w=weapons[i];change=w@idle['wpn_root'].inverted()
    pose['wpn_root']=w
    weight=ease(t/.15)*ease((DURATION-t)/.24)
    for side in ('l','r'):
        U,L,H,CL=[n+'_'+side for n in ('upperarm','lowerarm','hand','clavicle')]
        s0,e0,h0=[idle[n].translation for n in (U,L,H)]
        u0=e0-s0;l0=h0-e0;normal=u0.cross(l0).normalized()
        target=targets[side][i];h=target.translation
        # At both ends the original shoulder and its original bend plane take
        # over while the exact shaft grip continues to move along its curve.
        s,e=solutions[side][i]
        carry=target.to_quaternion()@idle[H].to_quaternion().inverted()
        f0=(carry@l0).normalized();f1=(h-e).normalized()
        fore=Quaternion().slerp(f0.rotation_difference(f1),weight)@f0
        e=h-fore*l0.length
        guide=s0.lerp(s,weight);s=e-(e-guide).normalized()*u0.length
        upper=e-s;fore=h-e
        bu=bind[L].translation-bind[U].translation;bl=bind[H].translation-bind[L].translation
        bn=bu.cross(bl).normalized();plane=upper.cross(fore).normalized()
        du=frame(upper,plane)@frame(bu,bn).inverted()
        hinge=frame(fore,plane)@frame(bl,bn).inverted()
        hand_delta=target.to_quaternion()@bind[H].to_quaternion().inverted()
        full=(hand_delta@bl).rotation_difference(fore)@hand_delta
        roll=axial(full@hinge.inverted(),fore.normalized())
        if side in rolls:roll=rolls[side]+(roll-rolls[side]+math.pi)%(2*math.pi)-math.pi
        rolls[side]=roll
        pose[CL]=idle[CL].copy();pose[CL].translation+=s-s0
        old_upper=u0.rotation_difference(upper)@idle[U].to_quaternion()
        old_lower=l0.rotation_difference(fore)@idle[L].to_quaternion()
        uq=old_upper.slerp(du@bind[U].to_quaternion(),weight)
        lq=old_lower.slerp(hinge@bind[L].to_quaternion(),weight)
        pose[U]=mat(s,uq,idle[U].to_scale())
        pose[L]=mat(e,lq,idle[L].to_scale())
        pose[H]=target
        for suffix,share in [('01',1.),('02',.5)]:
            n='upperarm_twist_'+suffix+'_'+side
            old=u0.rotation_difference(upper)@idle[n].to_quaternion()
            q=old.slerp(du@bind[n].to_quaternion(),weight)
            fraction=(idle[n].translation-s0).dot(u0)/u0.length_squared
            pose[n]=mat(s+upper*fraction,q,idle[n].to_scale())
            n='lowerarm_twist_'+suffix+'_'+side
            old=l0.rotation_difference(fore)@idle[n].to_quaternion()
            q=old.slerp(Quaternion(fore.normalized(),roll*share)@hinge@bind[n].to_quaternion(),weight)
            fraction=(idle[n].translation-e0).dot(l0)/l0.length_squared
            pose[n]=mat(e+fore*fraction,q,idle[n].to_scale())
    explicit={'wpn_root'}|{n for n in idle if n.startswith(('clavicle_','upperarm','lowerarm','hand_'))}
    done=set(explicit)
    def resolve(n):
        if n not in done:
            parent=parents[n];pose[n]=resolve(parent)@local[n] if parent else idle[n].copy();done.add(n)
        return pose[n]
    for n in idle:resolve(n)
    for side in ('l','r'):pose['ik_hand_'+side]=change@idle['ik_hand_'+side]
    if i in (0,len(times)-1):pose={n:m.copy() for n,m in idle.items()}
    poses.append(pose)

# Save directly to the sequence data model, preserving native bone axes and
# the FBX 100x wrapper; the editable Blender action has an explicit axis map.
output=[];previous={}
for pose in poses:
    native={}
    for n,m in pose.items():
        p,q,s=m.decompose();native[n]=mat(C@p*100,(C@q.to_matrix()@C).to_quaternion(),s)
    keys_out={}
    for n,m in native.items():
        parent=parents[n];local_m=native[parent].inverted()@m if parent else m
        p,q,s=local_m.decompose()
        if n in previous and q.dot(previous[n])<0:q.negate()
        previous[n]=q.copy();keys_out[n]=dict(p=list(p),q=list(q),s=list(s))
    output.append(keys_out)
(P/'motion.json').write_text(json.dumps(dict(fps=FPS,frames=output,skeleton=NATIVE['skeleton'],
    markers=[['Prepare',.15],['Contact',.233333333],['Follow',.283333333],['Recover',.8]])))

SOURCE=ROOT/'SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene.frame_set(0)
original={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
restlocal={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
correction={n:idle[n.lower()].inverted()@m for n,m in original.items()}
rig.animation_data_clear();rig.animation_data_create();act=bpy.data.actions.new('A_Warhammer_QuickReferenceV8');rig.animation_data.action=act;act.use_fake_user=True
previous={}
for i,pose in enumerate(poses):
    world={n:pose[n.lower()]@correction[n] for n in rest}
    for bone in rig.pose.bones:
        parent=world[bone.parent.name] if bone.parent else Matrix.Identity(4)
        bone.rotation_mode='QUATERNION';bone.matrix_basis=restlocal[bone.name].inverted()@parent.inverted()@world[bone.name]
        q=bone.rotation_quaternion.copy()
        if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
        previous[bone.name]=q.copy();bone.rotation_quaternion=q
        for ch in ('location','rotation_quaternion','scale'):bone.keyframe_insert(ch,frame=i,group=bone.name)
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for key in fc.keyframe_points:key.interpolation='LINEAR'
scene.render.fps=FPS;scene.frame_start=0;scene.frame_end=len(poses)-1;scene.frame_set(0)
# Resolve linked author libraries before moving the editable file.
bpy.ops.file.make_paths_absolute()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_QuickReferenceV8_Editable.blend'))
(P/'authored.json').write_text(json.dumps(dict(revision='ReferenceButtStrikeV8',fps=FPS,seconds=DURATION,
    source_video='_5pAl232f38',reference_active=[55.65,56.95],contact=.233333333,
    original=str(SOURCE),native_input='native-idle.json',runtime_tested=False,preview_rendered=False,
    scope='Two-hand shaft-butt quick strike; fixed native grips, whole arms, reference camera',
    depth='Three-dimensional adaptation; video does not provide rig or camera calibration'),indent=2))
print('HAMMER_REFERENCE_AUTHORED',len(output),'native frames')
