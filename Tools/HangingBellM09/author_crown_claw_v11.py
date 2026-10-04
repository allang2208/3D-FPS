"""Adapt M07's accepted Attack_D arm choreography to M09's two small arms.

Offline animation production only. Preserve the M09 mesh, bind, weights and
support arms. The donor is sampled, never edited or saved back to its source.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/HangingBellM09Meshy20261003'
OUT = ROOT/'CrownClawV11'
DONOR = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001/LibrarySweepV27/Motion/M07_LibrarySweep_V27.blend'
for folder in ('Authoring', 'Exports', 'Records'):
    (OUT/folder).mkdir(parents=True, exist_ok=True)
FPS, DURATION = 60, 1.1

def smooth(t):
    t = min(1., max(0., t))
    return t*t*t*(10.-15.*t+6.*t*t)

def envelope(t, a, b, c, d):
    return smooth((t-a)/(b-a))*(1.-smooth((t-c)/(d-c)))

def frame(y, normal):
    y = y.normalized()
    z = (normal-y*normal.dot(y)).normalized()
    return Matrix((y.cross(z).normalized(), y, z)).transposed().to_quaternion()

def body_frame(pose):
    across = (pose['upperarm_l'].translation-pose['upperarm_r'].translation).normalized()
    up = (pose['head'].translation-pose['pelvis'].translation).normalized()
    up = (up-across*up.dot(across)).normalized()
    return Matrix((across, up.cross(across), up)).transposed()

# The two authored M07 clips already carry the complete mirrored arm motion.
bpy.ops.wm.open_mainfile(filepath=str(DONOR))
source_rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and 'upperarm_r' in o.data.bones)
source_names = ['pelvis', 'head', 'spine_05', 'upperarm_l', 'upperarm_r']
for suffix in ('l', 'r'):
    source_names += [f'{name}_{suffix}' for name in ('lowerarm', 'hand', 'middle_01', 'index_01', 'pinky_01')]
source_rest = {n: source_rig.data.bones[n].matrix_local.copy() for n in source_names}
source_frames = {}
scene = bpy.context.scene
source_fps = scene.render.fps/scene.render.fps_base
for side, role in (('L', 'SweepLeft'), ('R', 'SweepRight')):
    action = bpy.data.actions['A_M07_'+role+'_LibrarySweepV27']
    source_rig.animation_data.action = action
    if action.slots:
        source_rig.animation_data.action_slot = action.slots[0]
    samples = []
    for i in range(121):
        f = float(action.frame_range[0])+i/FPS*source_fps
        scene.frame_set(math.floor(f), subframe=f % 1.)
        samples.append({n: source_rig.pose.bones[n].matrix.copy() for n in source_names})
    source_frames[side] = samples
(OUT/'Records/donor_motion.json').write_text(json.dumps({
    'source': str(DONOR), 'fps': FPS,
    'reference': {n: [list(row) for row in m] for n,m in source_rest.items()},
    'clips': {s: [{n: [list(row) for row in m] for n,m in p.items()} for p in frames]
              for s,frames in source_frames.items()},
    'source_modified': False}), encoding='utf8')

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RigV03/Authoring/M09_Rigged_v03.blend'))
rig = bpy.data.objects['M09_Rig_V03']
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = FPS, 1.
rig.animation_data_clear()
rig.animation_data_create()
for p in rig.pose.bones:
    for constraint in list(p.constraints):
        p.constraints.remove(constraint)
    p.rotation_mode = 'QUATERNION'
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local = {b.name: rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
         for b in rig.data.bones}
registration = body_frame(source_rest).inverted().to_quaternion()
calibration = {}
for side in ('L', 'R'):
    s = side.lower()
    su, sl, sh = [f'{n}_{s}' for n in ('upperarm', 'lowerarm', 'hand')]
    tu, tl, th = [f'small_{n}_{side}' for n in ('upperarm', 'forearm', 'hand')]
    source_upper = source_rest[sl].translation-source_rest[su].translation
    source_lower = source_rest[sh].translation-source_rest[sl].translation
    target_upper = rest[tl].translation-rest[tu].translation
    target_lower = rest[th].translation-rest[tl].translation
    source_normal = source_upper.cross(source_lower)
    if source_normal.length < 1e-4:
        source_normal = source_upper.cross(Vector((0., -1., 0.)))
    target_normal = target_upper.cross(target_lower)
    pairs = [(su, tu, source_upper, target_upper, source_normal, target_normal),
             (sl, tl, source_lower, target_lower, source_normal, target_normal),
             (sh, th, source_rest[f'middle_01_{s}'].translation-source_rest[sh].translation,
              rest[f'smallfinger_{side}_03_01'].translation-rest[th].translation,
              (source_rest[f'index_01_{s}'].translation-source_rest[sh].translation).cross(
                  source_rest[f'pinky_01_{s}'].translation-source_rest[sh].translation),
              (rest[f'smallfinger_{side}_02_01'].translation-rest[th].translation).cross(
                  rest[f'smallfinger_{side}_05_01'].translation-rest[th].translation))]
    calibration[side] = []
    for src, dst, sy, ty, sn, tn in pairs:
        # Constant anatomical reference registration; preserve the donor's full
        # rotation, including coordinated forearm/wrist roll, throughout the clip.
        correction = source_rest[src].to_quaternion().inverted()@frame(sy, sn)@frame(ty, tn).inverted()@rest[dst].to_quaternion()
        calibration[side].append((src, dst, correction))

def donor_time(t):
    # Retain source contact .50-.70 at target .35-.55. Cubic Hermite pacing
    # eases the surrounding windup/recovery without a change of speed at contact.
    knots = [(0., 0., 1.4), (.35, .50, 1.), (.55, .70, 1.), (.80, 1.30, 2.5), (1.10, 2., 2.)]
    t = min(DURATION, max(0., t))
    for (a,x,dx),(b,y,dy) in zip(knots,knots[1:]):
        if t <= b:
            u = (t-a)/(b-a)
            return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*(b-a)*dx+(-2*u**3+3*u*u)*y+(u**3-u*u)*(b-a)*dy
    return 2.

def sample(side, time):
    at = min(120., max(0., time*FPS))
    index = min(119, int(at))
    alpha = at-index
    return {n: source_frames[side][index][n].lerp(source_frames[side][index+1][n], alpha) for n in source_names}

action = bpy.data.actions.new('A_M09_CrownClaw_V11')
rig.animation_data.action = action
action.use_fake_user = True
scene.frame_start, scene.frame_end = 1, round(DURATION*FPS)+1
names = [b.name for b in rig.data.bones if b.use_deform]
for i in range(round(DURATION*FPS)+1):
    t = i/FPS
    for p in rig.pose.bones:
        p.location = (0.,0.,0.)
        p.rotation_quaternion = Quaternion()
        p.scale = (1.,1.,1.)
    lead = sample('R', donor_time(t))
    chest_delta = registration@lead['spine_05'].to_quaternion()@source_rest['spine_05'].to_quaternion().inverted()@registration.inverted()
    chest_q = Quaternion().slerp(chest_delta, .12*envelope(t,0.,.27,.64,DURATION))
    # Hanging support owns root/large arms. Only the lower torso softly follows.
    name = 'spine_03'
    rig.pose.bones[name].rotation_quaternion = rest[name].to_quaternion().inverted()@chest_q@rest[name].to_quaternion()
    target_global = {}
    for bone in rig.data.bones:
        target_global[bone.name] = (target_global[bone.parent.name] if bone.parent else Quaternion())@local[bone.name].to_quaternion()@rig.pose.bones[bone.name].rotation_quaternion
    for side, delay in (('R',0.),('L',.025)):
        ts = max(0., t-delay)
        source = sample(side, donor_time(ts))
        arm_weight = envelope(t,delay,.28+delay,.63+delay,DURATION)
        wrist_weight = envelope(t,delay,.28+delay,.68+delay,DURATION)
        # Remove the standing donor's torso turn; the original relative shoulder,
        # elbow and wrist choreography then follows M09's supported lower torso.
        mapping = chest_q@registration@source_rest['spine_05'].to_quaternion()@source['spine_05'].to_quaternion().inverted()
        desired_parent = chest_q@rest['spine_03'].to_quaternion()
        for src,dst,correction in calibration[side]:
            desired = mapping@source[src].to_quaternion()@correction
            pose_q = local[dst].to_quaternion().inverted()@desired_parent.inverted()@desired
            weight = wrist_weight if src.startswith('hand_') else arm_weight
            rig.pose.bones[dst].rotation_quaternion = Quaternion().slerp(pose_q,weight)
            desired_parent = desired
        # Preserve the existing finger chain/skin, just open then hook the tips.
        spread = envelope(t,delay,.26+delay,.34+delay,.49+delay)
        rake = envelope(t,.32+delay,.45+delay,.59+delay,DURATION)
        for digit in range(1,6):
            for joint in range(1,4):
                name = f'smallfinger_{side}_{digit:02d}_{joint:02d}'
                factor = .65 if digit == 1 else 1.
                rig.pose.bones[name].rotation_quaternion = Quaternion((1.,0.,0.),math.radians((-9.*spread+7.*rake)*factor))
    for n in names:
        for channel in ('location','rotation_quaternion','scale'):
            rig.pose.bones[n].keyframe_insert(channel,frame=i+1,group=n)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx = OUT/'Exports/A_M09_CrownClaw_V11.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0,add_leaf_bones=False,use_armature_deform_only=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_CrownClaw_V11.blend'),compress=True)
(OUT/'Records/motion_manifest.json').write_text(json.dumps({
    'version':'CrownClawV11','source':str(DONOR),
    'original_source':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D',
    'source_policy':'Reuse M07 accepted attack arm choreography; adapt to supported nonhumanoid small arms',
    'fps':FPS,'duration':DURATION,'frames':67,'contact':[.35,.55],'left_delay':.025,
    'damage_multiplier':.55,'cooldown':2.5,'root_motion':False,
    'geometry_modified':False,'bind_modified':False,'weights_modified':False,
    'support_arms_preserved':True,'tested':False,'rendered':False,
    'license':'Existing local ZombieAnimationPack derivative; no new acquisition or redistribution',
    'file':str(fbx)},indent=2),encoding='utf8')
print('M09_CROWN_CLAW_V11_AUTHORED',flush=True)
