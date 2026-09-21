"""Editable Manny cast source. Runtime uses the same semantic pose JSON and a
per-rig solver, preserving live right-hand weapon animation. No rendering/tests.
"""
import bpy,json,math,re,sys,argparse
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

P=Path(__file__).parent
ROOT=P.parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=ROOT/'SourceAssets/CastingPalmPush20260921/ImpactV9')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUTPUT=args.output_dir.resolve();OUTPUT.mkdir(parents=True,exist_ok=True)
CONFIG=ROOT/'Content/ColdSteelData/Skills/fireball_hand_pose.json'
cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
timing_path=ROOT/'Source/FPSGAME/Skills/FPSFireballComponent.h'
motion_path=ROOT/'Source/FPSGAME/Skills/FireballCastMotion.h'
native_clocks=timing_path.exists() and motion_path.exists()
timing_header=timing_path.read_text(encoding='utf-8') if native_clocks else ''
motion_header=motion_path.read_text(encoding='utf-8') if native_clocks else ''
clock_config=json.loads((P/'motion_config.json').read_text(encoding='utf-8'))
def duration(name):
    if not native_clocks:return clock_config['durations'][name]
    return float(re.search(r'float '+name+r'=([.0-9]+)f;',timing_header).group(1))
RAISE=duration('RaiseDuration');READY=duration('ReleaseEntryDuration')
RELEASE=duration('ReleaseDuration');CONTACT=duration('LaunchContactTime');RECOVER=duration('RecoveryDuration')
def motion_scalar(name,fallback):
    return float(re.search(r'float '+name+r'=([.0-9]+)f;',motion_header).group(1)) if native_clocks else fallback
RELEASE_TOTAL=motion_scalar('ReleaseTotalSeconds',clock_config['durations']['ReleaseTotalSeconds'])
PUSH_SPEED=motion_scalar('ReleasePushSpeed',clock_config['release_push_speed'])
ENTRY_SPEED=motion_scalar('ReleaseEntrySpeed',clock_config['release_entry_speed'])
IMPACT={key:motion_scalar(key,value) for key,value in clock_config['impact'].items()}
# Bake the default (1x haste) clock; preserve the moving stages and derive the
# hold from the requested complete-cast budget.
READY/=ENTRY_SPEED;RELEASE/=PUSH_SPEED;CONTACT/=PUSH_SPEED
RELEASE_HOLD=max(0,RELEASE_TOTAL-READY-RELEASE-RECOVER)
def keys(name):
    if not native_clocks:return clock_config['curves'][name]
    block=re.search(name+r'\[\]=\{(.*?)\};',motion_header,re.S).group(1)
    return [tuple(float(v.strip().rstrip('f')) for v in group.split(',')) for group in re.findall(r'\{([^{}]+)\}',block)]
GATHER_KEYS=keys('GatherKeys');PUSH_KEYS=keys('PushKeys');RETURN_KEYS=keys('ReturnKeys')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'GASPTraversal20260910/Native/TraversalArms_Editable.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['SK_M4_Infima']
arms=bpy.data.objects['SK_Manny_Arms_Export']
rig.animation_data_create();rig.animation_data.action=bpy.data.actions['M4_idle']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
entry={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
entry_local={n:entry[parents[n]].inverted()@m if parents[n] else m for n,m in entry.items()}
def is_left(n):
    if not n.endswith('_l'):return False
    while n:
        if n=='clavicle_l':return True
        n=parents[n]
    return False
left=[n for n in rest if is_left(n)]
for ob in list(bpy.data.objects):
    if ob not in (rig,arms):bpy.data.objects.remove(ob,do_unlink=True)
rig.animation_data_clear()
for bone in rig.pose.bones:
    for c in list(bone.constraints):bone.constraints.remove(c)
    bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
rig.name='SK_FireballCasting_Rig'

# UE camera axes -> Blender camera axes. Reflection applies to positions and
# semantic frames; the product of source/target frames remains a proper rotation.
C=Matrix(((0,1,0),(1,0,0),(0,0,1)))
def pos(key):return C@Vector(cfg[key])*.01
def ease(t):
    t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
def sample_curve(points,t):
    if t<=points[0][0]:return points[0][1]
    for a,b in zip(points,points[1:]):
        if t<b[0]:
            span=b[0]-a[0];u=(t-a[0])/span;u2=u*u;u3=u2*u
            return (2*u3-3*u2+1)*a[1]+(u3-2*u2+u)*span*a[2]+(-2*u3+3*u2)*b[1]+(u3-u2)*span*b[2]
    return points[-1][1]
def arc(a,b,c,d,t):
    v=1-t;return a*(v*v*v)+b*(3*v*v*t)+c*(3*v*t*t)+d*(t*t*t)
def semantic_frame(forward,normal):
    f=forward.normalized();z=(normal-f*normal.dot(f)).normalized()
    return Matrix((f,f.cross(z),z)).transposed()

def forearm_frame(direction,across):
    x=direction.normalized();y=(across-x*across.dot(x)).normalized()
    return Matrix((x,y,x.cross(y))).transposed().to_quaternion()
def ue_frame(f,n):
    f=Vector(f).normalized();z=Vector(n);z=(z-f*z.dot(f)).normalized()
    return Matrix((f,z.cross(f),z)).transposed().to_quaternion()
hold=ue_frame(cfg['gather_forward'],cfg['gather_normal'])
mid=ue_frame((Vector(cfg['gather_forward'])+Vector(cfg['release_forward']))*.5,cfg['release_mid_normal'])
release=ue_frame(cfg['release_forward'],cfg['release_normal'])
def palm(t):
    q=hold.slerp(mid,t).slerp(mid.slerp(release,t),t)
    return C@q.to_matrix()
A0=rest['upperarm_l'].translation;E0=rest['lowerarm_l'].translation;H0=rest['hand_l'].translation
RU=E0-A0;RL=H0-E0;L1=RU.length;L2=RL.length
ref_normal=(rest['pinky_01_l'].translation-H0).cross(rest['index_01_l'].translation-H0).normalized()
ref_palm=semantic_frame(rest['middle_01_l'].translation-H0,ref_normal)
correction=ref_palm.inverted()@rest['hand_l'].to_3x3()
def blend(a,b,w):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),a.to_scale().lerp(b.to_scale(),w))
def release_motion(seconds,detached=False):
    clock=min(seconds,RELEASE)/max(.01,min(CONTACT,RELEASE));push=sample_curve(PUSH_KEYS,clock)
    w=pos('windup_wrist' if detached else 'gather_wrist').lerp(pos('release_wrist'),push)
    u=max(0,min(1,push));w+=C@Vector((0,-.8,-1.4))*.01*(16*u*u*(1-u)*(1-u))
    start=.48 if detached else 0.;rel=start+(1-start)*ease((clock-.10)/.90)
    a=pos('shoulder').lerp(pos('release_shoulder'),push)
    p=pos('elbow_pole').lerp(pos('release_elbow_pole'),push)
    since_contact=seconds-CONTACT
    if 0<since_contact<IMPACT['ImpactDuration']:
        fade=ease(since_contact/IMPACT['ImpactAttackSeconds'])*(1-ease(since_contact/IMPACT['ImpactDuration']))
        angle=2*math.pi*IMPACT['ImpactFrequencyHz']*since_contact;wave=math.sin(angle)
        offset=C@Vector((-IMPACT['ImpactRecoilCM']*wave,IMPACT['ImpactLateralCM']*math.sin(angle*1.5),IMPACT['ImpactLiftCM']*wave))*(.01*fade)
        w+=offset;a+=offset;p+=offset
    return w,a,p,(palm(rel)@correction).to_quaternion(),rel,1.,1.

def motion(phase,t):
    ew=entry['hand_l'].translation;ea=entry['upperarm_l'].translation;ep=entry['lowerarm_l'].translation
    eq=entry['hand_l'].to_quaternion()
    if phase=='PushHold':return release_motion(RELEASE+t*RELEASE_HOLD)
    if phase=='CastDetached':
        age=t*(READY+RELEASE+RELEASE_HOLD+RECOVER)
        if age<READY:return motion('ReleaseWindup',age/READY)
        if age<READY+RELEASE:return motion('ReleaseDetached',(age-READY)/RELEASE)
        if age<READY+RELEASE+RELEASE_HOLD:return motion('PushHold',(age-READY-RELEASE)/RELEASE_HOLD)
        return motion('Recover',(age-READY-RELEASE-RELEASE_HOLD)/RECOVER)
    if phase in ('Recover','GatherRecover'):
        w,a,p,q,rel,fingers,weight=motion('Gather' if phase=='GatherRecover' else 'PushHold',1.)
        u=sample_curve(RETURN_KEYS,t)
        return (arc(w,w+pos('recovery_depart'),ew+pos('recovery_approach'),ew,u),
            a.lerp(ea,ease(t)),p.lerp(ep,ease((t-.04)/.96)),
            q.slerp(eq,ease(t/.92)),rel,fingers*(1-ease((t-.08)/.76)),weight*(1-ease((t-.20)/.80)))
    if phase=='Gather':
        w=arc(ew,ew+pos('gather_depart'),pos('gather_wrist')+pos('gather_approach'),pos('gather_wrist'),sample_curve(GATHER_KEYS,t))
        return (w,ea.lerp(pos('shoulder'),ease(t/.84)),ep.lerp(pos('elbow_pole'),ease((t-.025)/.90)),
            eq.slerp((palm(0)@correction).to_quaternion(),ease((t-.10)/.80)),0.,ease((t-.04)/.72),ease(t/.16))
    if phase=='ReleaseWindup':
        w=arc(ew,ew+pos('windup_depart'),pos('windup_wrist')+pos('windup_approach'),pos('windup_wrist'),ease(t))
        return (w,ea.lerp(pos('shoulder'),ease(t/.85)),ep.lerp(pos('elbow_pole'),ease((t-.03)/.92)),
            eq.slerp((palm(.48)@correction).to_quaternion(),ease((t-.06)/.90)),.48,ease((t-.05)/.80),ease(t/.20))
    if phase=='Hold':return pos('gather_wrist'),pos('shoulder'),pos('elbow_pole'),(palm(0)@correction).to_quaternion(),0.,1.,1.
    return release_motion(t*RELEASE,phase=='ReleaseDetached')

def solve(phase,t):
    W,A,pole,HQ,rel,finger_blend,layer_weight=motion(phase,t)
    reach=W-A;supported=(L1+L2)*.93
    if reach.length>supported:A+=reach.normalized()*(reach.length-supported)
    d=W-A;length=max(1e-6,min(d.length,L1+L2-.00001));direction=d.normalized();W=A+direction*length
    bend=pole-A;bend-=direction*bend.dot(direction);bend.normalize()
    along=(L1*L1-L2*L2+length*length)/(2*length)
    E=A+direction*along+bend*math.sqrt(max(0,L1*L1-along*along))
    ud=(E-A).normalized();ld=(W-E).normalized();normal=ud.cross(ld).normalized();rn=RU.cross(RL).normalized()
    uq=(semantic_frame(ud,normal)@semantic_frame(RU,rn).inverted()@rest['upperarm_l'].to_3x3()).to_quaternion()
    hand_deform=HQ@rest['hand_l'].to_quaternion().inverted()
    across=ref_palm.col[1]
    forearm_deform=forearm_frame(ld,hand_deform@across)@forearm_frame(RL,across).inverted()
    fq=forearm_deform@rest['lowerarm_l'].to_quaternion()
    upper_across=(uq@rest['upperarm_l'].to_quaternion().inverted())@across
    palm_across=hand_deform@across
    upper_side=(upper_across-ud*upper_across.dot(ud)).normalized()
    palm_side=(palm_across-ud*palm_across.dot(ud)).normalized()
    roll=math.atan2(ud.dot(upper_side.cross(palm_side)),upper_side.dot(palm_side))*.18
    roll=max(-math.radians(12),min(math.radians(12),roll))*ease(rel)
    uq=Quaternion(ud,roll)@uq
    recovery_t=t if phase in ('Recover','GatherRecover') else None
    if phase=='CastDetached':
        age=t*(READY+RELEASE+RELEASE_HOLD+RECOVER)
        if age>=READY+RELEASE+RELEASE_HOLD:recovery_t=(age-READY-RELEASE-RELEASE_HOLD)/RECOVER
    if recovery_t is not None:
        def return_roll(name,rest_axis,axis,authored):
            source=entry[name].to_quaternion()
            source_axis=(source@rest[name].to_quaternion().inverted())@rest_axis.normalized()
            aligned=source_axis.rotation_difference(axis)@source
            return authored.slerp(aligned,ease(recovery_t))
        uq=return_roll('upperarm_l',RU,ud,uq)
        fq=return_roll('lowerarm_l',RL,ld,fq)
    result={n:m.copy() for n,m in entry.items()}
    hand_frame=HQ.to_matrix()@rest['hand_l'].to_3x3().inverted()@ref_palm
    for n in left:
        parent=parents[n]
        if n=='clavicle_l':
            m=entry[n].copy();m.translation=A+entry[n].translation-entry['upperarm_l'].translation
        elif n=='upperarm_l':m=Matrix.LocRotScale(A,uq,Vector((1,1,1)))
        elif n=='lowerarm_l':m=Matrix.LocRotScale(E,fq,Vector((1,1,1)))
        elif n=='hand_l':m=Matrix.LocRotScale(W,HQ,Vector((1,1,1)))
        else:
            m=result[parent]@local[n]
            # Twist helpers inherit the complete parent-segment deformation.
            # Fractional roll caused the same skin collapse fixed in RuneSword V4.
            parts=n.split('_')
            if parts[0] in cfg['digits'] and len(parts)==3 and parts[1].isdigit():
                k=int(parts[1])-1;digit=cfg['digits'][parts[0]]
                if 0<=k<=2:
                    nxt=f'{parts[0]}_{k+2:02d}_l'
                    if nxt in rest:rd=rest[nxt].translation-rest[n].translation
                    else:rd=rest[n].to_quaternion()@(rest[parent].to_quaternion().inverted()@(rest[n].translation-rest[parent].translation))
                    angle=math.radians(digit['spread'][k]);flex=math.radians(digit['gather_flex'][k]*(1-rel)+digit['release_flex'][k]*rel)
                    target=hand_frame@Vector((math.cos(flex)*math.cos(angle),math.cos(flex)*math.sin(angle),math.sin(flex)))
                    q=(semantic_frame(target,hand_frame.col[2])@semantic_frame(rd,ref_normal).inverted()@rest[n].to_3x3()).to_quaternion()
                    q_local=result[parent].to_quaternion().inverted()@q
                    delay={'thumb':0.,'index':.015,'middle':.025,'ring':.05,'pinky':.075}[parts[0]]+k*.015
                    finger_weight=max(0,min(1,(finger_blend-delay)/(1-delay)))
                    q=result[parent].to_quaternion()@entry_local[n].to_quaternion().slerp(q_local,finger_weight)
                    m=Matrix.LocRotScale(m.translation,q,Vector((1,1,1)))
        result[n]=m
    locals_goal={n:result[parents[n]].inverted()@result[n] for n in left}
    for n in left:result[n]=result[parents[n]]@blend(entry_local[n],locals_goal[n],layer_weight)
    return result

out=OUTPUT/'Export';out.mkdir(exist_ok=True)
scene.render.fps=300;scene.render.fps_base=1.
records=[]
for phase,seconds in [('Gather',RAISE),('GatherRecover',RECOVER),('ReleaseWindup',READY),('ReleaseDetached',RELEASE),('PushHold',RELEASE_HOLD),('Recover',RECOVER),('Hold',1.),('Release',RELEASE),('CastDetached',READY+RELEASE+RELEASE_HOLD+RECOVER)]:
    action=bpy.data.actions.new('A_Fireball_'+phase);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    end=round(seconds*300);scene.frame_start=0;scene.frame_end=end
    previous={}
    for frame in range(end+1):
        values=solve(phase,frame/max(1,end))
        for n in rest:
            if n not in left and frame not in (0,end):continue
            b=rig.pose.bones[n];parent=parents[n]
            basis=local[n].inverted()@(values[parent].inverted()@values[n] if parent else values[n])
            loc,q,scale=basis.decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();b.location=loc;b.rotation_quaternion=q;b.scale=scale
            for key in ('location','rotation_quaternion','scale'):b.keyframe_insert(key,frame=frame,group=n)
    # Dense source frames with linear local interpolation, matching runtime's
    # continuous trajectories; no extra easing by the DCC/exporter.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    for ob in (rig,arms):ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(out/f'A_Fireball_{phase}.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,mesh_smooth_type='FACE',use_tspace=True)
    records.append({'name':action.name,'fps':300,'frames':[0,end],'duration':seconds,'loop':phase=='Hold'})
rig.animation_data.action=bpy.data.actions['A_Fireball_Gather']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=round(RAISE*300);scene.frame_set(scene.frame_end)
camdata=bpy.data.cameras.new('Casting_Source_Camera');camera=bpy.data.objects.new('Casting_Source_Camera',camdata)
scene.collection.objects.link(camera);camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0);camdata.lens=18;scene.camera=camera
scene.render.resolution_x=1920;scene.render.resolution_y=1080
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'Casting_PalmPush_Editable.blend'))
(OUTPUT/'fireball_hand_pose.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
(OUTPUT/'authoring.json').write_text(json.dumps({'references':[str(P/'reference-gather.jpg'),str(OUTPUT/'reference-palm-push.jpg')],
    'source_mesh':'SK_Manny_Arms_Export','pose_config':str(CONFIG),'clips':records,
    'release_contact_seconds':CONTACT,'release_windup_seconds':READY,
    'motion_revision':'Outward palm V9: one-second total, stronger/slower damped whole-arm impact, fast entry/push and V6 recovery retained',
    'release_hold_seconds':RELEASE_HOLD,'release_push_speed':PUSH_SPEED,'release_entry_speed':ENTRY_SPEED,'impact':IMPACT,
    'release_total_seconds':RELEASE_TOTAL,
    'hold_clock':'derived from 1-second default total minus ready/push/recovery; derived hold remains real-time while moving stages use gesture haste',
    'timing_source':'Source/FPSGAME/Skills/FireballCastMotion.h + FPSFireballComponent.h' if native_clocks else 'motion_config.json (publication authoring snapshot)',
    'detached_hover':True,'hold_clip_usage':'reference pose only; runtime releases the hand after gathering',
    'runtime':'FPSCastingMeshComponent retargets palm and finger directions to each equipped skeleton',
    'renders_or_tests_run':False},indent=2),encoding='utf-8')
print('FIREBALL_CAST_SOURCE_SAVED',len(records))
