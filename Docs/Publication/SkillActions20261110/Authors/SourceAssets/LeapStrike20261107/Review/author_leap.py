"""Leap-only continuous native pose. Source stages are preserved as weapon/grip keys.
Whole arm reconstruction uses native bind hinges, fixed lengths and twist stations.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
SOURCE=ROOT/'SourceAssets/WarhammerQuickReference20261107'
FPS=120
DURATION=1.8333333333333333
NATIVE=json.loads((SOURCE/'native-idle.json').read_text())
INPUT=json.loads((SOURCE/'native-author-inputs.json').read_text())
parents=INPUT['parents']
C=Matrix.Diagonal(Vector((1,-1,1)))
def mat(p,q,s=(1,1,1)):return Matrix.LocRotScale(Vector(p),q,Vector(s))
idle={n:mat(k['p'],Quaternion(k['q']),k['s']) for n,k in INPUT['world'].items()}
mesh_bind=json.loads((SOURCE/'Review/current-mesh.json').read_text())['bones']
bind={n:mat(C@Vector(k['p'])*.01,(C@Quaternion(k['q']).to_matrix()@C).to_quaternion(),k['s']) for n,k in mesh_bind.items()}
local={n:idle[p].inverted()@m if p else m.copy() for n,m in idle.items() for p in [parents[n]]}
def ease(t):
 t=max(0.,min(1.,t));return t*t*t*(10-15*t+6*t*t)
def blend(a,b,u):
 ap,aq,asc=a.decompose();bp,bq,bsc=b.decompose();return mat(ap.lerp(bp,u),aq.slerp(bq,u),asc.lerp(bsc,u))
raw=json.loads((P/'Before/frames-120.json').read_text(encoding='utf-8-sig'))['frames']
def source(t,camera=False):
 f=min(raw,key=lambda f:abs(f['age']-t));out={}
 mc=f['mesh_to_camera'];mc=mat(mc['p'],Quaternion(mc['q']),mc['s'])
 axes=Matrix(((0,1,0),(1,0,0),(0,0,1)))
 for n,k in f['bones'].items():
  m=mat(k['p'],Quaternion(k['q']),k['s'])
  if camera:
   m=mc@m;p=axes@m.translation*.01;q=(axes@m.to_3x3()@C).to_quaternion()
  else:p=C@m.translation*.01;q=(C@m.to_quaternion().to_matrix()@C).to_quaternion()
  out[n]=mat(p,q,m.to_scale())
 return out
charge=source(.5);raised=source(.75);land=source(1.25,True)
raised['wpn_root'].translation+=Vector((-.07,.12,-.28))
land['wpn_root'].translation=Vector((0,.34,-.30))
def relative(p,s):return p['wpn_root'].inverted()@p['hand_'+s]
# The source terminal poses keep their shaft contacts; intermediate grips interpolate
# around the handle instead of passing through it.
grips={s:[idle['wpn_root'].inverted()@idle['hand_'+s],relative(charge,s),relative(source(.75),s),relative(source(1.25,True),s)] for s in ('l','r')}
def gripblend(a,b,u):
 m=blend(a,b,u);pa,pb=a.translation,b.translation
 a0=math.atan2(pa.y,pa.x);d=(math.atan2(pb.y,pb.x)-a0+math.pi)%(2*math.pi)-math.pi
 rad=(1-u)*math.hypot(pa.x,pa.y)+u*math.hypot(pb.x,pb.y)
 m.translation=Vector((rad*math.cos(a0+d*u),rad*math.sin(a0+d*u),(1-u)*pa.z+u*pb.z));return m
# Native uppercut load is already smooth; resample without its broken arm IK.
def state(t):
 if t<.5:
  i=next((i for i,f in enumerate(raw) if f['age']>=t),0)
  a,b=raw[max(0,i-1)],raw[i];u=max(0,min(1,(t-a['age'])/max(1e-6,b['age']-a['age'])))
  w=blend(source(a['age'])['wpn_root'],source(b['age'])['wpn_root'],u)
  w=blend(idle['wpn_root'],w,ease(t/.10))
  return w,{s:gripblend(grips[s][0],grips[s][1],ease(t/.5)) for s in grips}
 if t<.83:
  u=ease((t-.5)/.33);return blend(charge['wpn_root'],raised['wpn_root'],u),{s:gripblend(grips[s][1],grips[s][2],u) for s in grips}
 if t<1.04:return raised['wpn_root'],{s:grips[s][2] for s in grips}
 if t<1.25:
  u=ease(((t-1.04)/.21)**1.25);return blend(raised['wpn_root'],land['wpn_root'],u),{s:gripblend(grips[s][2],grips[s][3],u) for s in grips}
 if t<1.39:return land['wpn_root'],{s:grips[s][3] for s in grips}
 u=ease((t-1.39)/.44)
 w=blend(land['wpn_root'],idle['wpn_root'],u)
 w.translation.z-=.22*math.sin(math.pi*u)**2
 # Release the forearm pronation while the supported hammer lowers, then lift
 # back into the idle diagonal. This prevents the elbow flipping in view.
 angle=ease((t-1.52)/.31)
 w=mat(w.translation,land['wpn_root'].to_quaternion().slerp(idle['wpn_root'].to_quaternion(),angle),w.to_scale())
 g=ease((t-1.39)/.24)
 return w,{s:gripblend(grips[s][3],grips[s][0],g) for s in grips}
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def axial(q,axis):
    v=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (v+math.pi)%(2*math.pi)-math.pi

def arm(side,target,previous,t):
    U,L,H,CL=[n+'_'+side for n in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[idle[n].translation for n in (U,L,H)]
    u0=e0-s0;l0=h0-e0;h=target.translation
    s0=s0.copy();s0.z-=.08*ease((t-1.39)/.08)*ease((DURATION-t)/.15)
    hand_delta=target.to_quaternion()@bind[H].to_quaternion().inverted()
    neutral=(hand_delta@(bind[H].translation-bind[L].translation)).normalized()
    desired=Vector((.32,.70,.64) if side=='l' else (.38,.65,.66)).normalized()
    pole=desired-neutral*desired.dot(neutral)
    if pole.length<1e-6:pole=neutral.cross(Vector((0,0,1)))
    pole.normalize();best=None;sign=1 if side=='r' else -1
    for bend in range(0,31,3):
      for around in range(-180,180,10):
        radial=Quaternion(neutral,math.radians(around))@pole
        fore=neutral*math.cos(math.radians(bend))+radial*math.sin(math.radians(bend))
        e=h-fore*l0.length
        upper=(e-s0).normalized();shoulder=e-upper*u0.length
        visible=max(0.,shoulder.z+max(0.,shoulder.y)*.80+.095)
        cost=16*(shoulder-s0).length_squared+.18*fore.angle(desired)**2
        cost+=15*max(0.,.075-sign*shoulder.x)**2+800*visible**2
        cost+=160*max(0.,shoulder.y-.035)**2+.015*math.radians(bend)**2
        if previous:cost+=2*(e-previous['e']).length_squared
        if best is None or cost<best['cost']:best=dict(cost=cost,s=shoulder,e=e)
    return best

times=[i/FPS for i in range(round(DURATION*FPS)+1)]
states=[state(t) for t in times];weapons=[s[0] for s in states]
targets={s:[w@g[s] for w,g in states] for s in ('l','r')}
solutions={}
for side in ('l','r'):
    raw=[];prev=None
    for i,target in enumerate(targets[side]):prev=arm(side,target,prev,times[i]);raw.append(prev)
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
        ids=range(max(0,i-8),min(len(raw),i+9));ws=[math.exp(-.5*((j-i)/3.)**2) for j in ids]
        roll=sum(raw[j]*w for j,w in zip(ids,ws))/sum(ws)
        plane=Quaternion(fore,roll)@normal
        upper=Quaternion(plane,-flex)@fore;s,e=solutions[side][i]
        solutions[side][i]=(e-upper*length,e)

poses=[];rolls={}
for i,t in enumerate(times):
    pose={n:m.copy() for n,m in idle.items()};w=weapons[i];change=w@idle['wpn_root'].inverted()
    pose['wpn_root']=w
    weight=ease(t/.12)*ease((DURATION-t)/.16)
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
    markers=[['Takeoff',.5],['Contact',1.25],['Recover',1.39]])))

SOURCE=ROOT/'SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene.frame_set(0)
original={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
restlocal={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
correction={n:idle[n.lower()].inverted()@m for n,m in original.items()}
rig.animation_data_clear();rig.animation_data_create();act=bpy.data.actions.new('A_Warhammer_LeapStrikeV2');rig.animation_data.action=act;act.use_fake_user=True
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
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_LeapStrikeV2_Editable.blend'))

head=land['wpn_root']@(C@Vector((.150894263,.002343908,.972475657))*.01)
(P/'contact-head.json').write_text(json.dumps(dict(camera_cm=[head.y*100,head.x*100,head.z*100])))
(P/'authored-poses.json').write_text(json.dumps([{n:dict(p=list(m.translation),q=list(m.to_quaternion()),s=list(m.to_scale())) for n,m in pose.items()} for pose in poses]))
print('LEAP_CONTINUOUS_AUTHORED',len(output),'frames',list(head))
