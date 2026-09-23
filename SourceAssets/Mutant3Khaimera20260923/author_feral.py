"""Bake Khaimera motion onto the existing Mutant3 skin without changing its rest pose."""
import bpy, json, math, statistics
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).parent
BASE = ROOT.parent / 'Mutant3Meshy20260915/godot_runner/Mutant3_Meshy_CombatBase.blend'
OUT = ROOT / 'final'
FPS = 60
META = json.loads((ROOT / 'native_retarget.json').read_text())
SOURCES = ['Idle_NonAdditive', 'Jog_Fwd', 'TravelMode_Fwd', 'RMB_60fps',
           'Melee_A_Fast', 'Melee_B_Fast', 'Melee_C_Fast']

def activate(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action and action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True

motion = {}
for name in SOURCES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / 'native_retarget' / ('A_Mutant3_KhaiRaw_' + name + '.fbx')))
    donor = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    action = donor.animation_data.action
    activate(donor, action)
    scene = bpy.context.scene
    rate = scene.render.fps / scene.render.fps_base
    start = action.frame_range[0]
    duration = META['A_Mutant3_KhaiRaw_' + name]['seconds']
    frames = []
    for i in range(round(duration * FPS) + 1):
        f = start + min(duration, i / FPS) * rate
        scene.frame_set(math.floor(f), subframe=f % 1)
        frames.append({b.name: donor.matrix_world @ b.matrix for b in donor.pose.bones})
    motion[name] = dict(duration=duration, frames=frames,
                        rest={b.name: donor.matrix_world @ b.matrix_local for b in donor.data.bones})

bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.context.scene
scene.render.fps = FPS
scene.render.fps_base = 1
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
world_rest = {n: rig.matrix_world @ m for n, m in rest.items()}
inv = rig.matrix_world.inverted()
ordered = list(rig.pose.bones)
for pb in ordered:
    pb.rotation_mode = 'QUATERNION'

def smooth(x):
    x = max(0, min(1, x))
    return x*x*(3-2*x)

def sample(name, time):
    data = motion[name]
    index = max(0, min(time * FPS, len(data['frames'])-1))
    lo = int(index)
    hi = min(lo+1, len(data['frames'])-1)
    weight = index-lo
    return {n: data['frames'][lo][n].lerp(data['frames'][hi][n], weight) for n in rest}

def blend(a, b, w):
    return {n: a[n].lerp(b[n], w) for n in rest}

# The source RMB starts with takeoff. Add an explicit readable anticipation from
# its planted deep landing pose, then reuse its launch / air / impact choreography.
idle_pose = sample('Idle_NonAdditive', 0)
crouch_pose = sample('RMB_60fps', .9)
launch_pose = sample('RMB_60fps', .08)

CLIPS = {
    'FeralIdle': ('Idle_NonAdditive', round(motion['Idle_NonAdditive']['duration']*FPS)/FPS, True),
    'FeralRun': ('Jog_Fwd', 2.0, True),
    'FeralSprint': ('TravelMode_Fwd', 76/FPS, True),
    'ClawA': ('Melee_A_Fast', .5, False),
    'ClawB': ('Melee_B_Fast', .5, False),
    'ClawC': ('Melee_C_Fast', .5, False),
    'PounceWindup': ('RMB_60fps', .6, False),
    'PounceFlight': ('RMB_60fps', .65, False),
    'PounceLand': ('RMB_60fps', .8, False),
}

def set_pose(data, src, role):
    mats = {}
    for pb in ordered:
        name = pb.name
        bone = pb.bone
        r = rest[name]
        delta = data[name].to_quaternion() @ motion[src]['rest'][name].to_quaternion().inverted()
        q = (inv.to_quaternion() @ delta @ world_rest[name].to_quaternion()).normalized()
        if bone.parent:
            pos = mats[bone.parent.name] @ (rest[bone.parent.name].inverted() @ r).translation
            if name == 'Hips':
                # Preserve pelvis compression/bob; the previous runner bake omitted it.
                offset = data[name].translation - motion[src]['rest'][name].translation
                if role == 'PounceFlight':
                    # Capsule ballistic movement owns elevation; retain leg tuck and
                    # torso rotation without adding the source's vertical travel twice.
                    offset.z = launch_pose[name].translation.z - motion[src]['rest'][name].translation.z
                pos += inv.to_3x3() @ offset
        else:
            pos = r.translation.copy()
        m = Matrix.LocRotScale(pos, q, Vector((1,1,1)))
        mats[name] = m
        pb.matrix_basis = ((rest[bone.parent.name].inverted() @ r).inverted() @ mats[bone.parent.name].inverted() @ m
                           if bone.parent else r.inverted() @ m)
    bpy.context.view_layer.update()
    # Resolve body-size penetration during grounded motion; air poses are not planted.
    if role != 'PounceFlight':
        deps = bpy.context.evaluated_depsgraph_get()
        low = float('inf')
        for mesh in meshes:
            obj = mesh.evaluated_get(deps)
            data_mesh = obj.to_mesh()
            low = min(low, min((obj.matrix_world @ v.co).z for v in data_mesh.vertices))
            obj.to_mesh_clear()
        hips = rig.pose.bones['Hips']
        m = hips.matrix.copy()
        m.translation += inv.to_3x3() @ Vector((0,0,max(0,.003-low)))
        hips.matrix = m
        bpy.context.view_layer.update()

outputs = {}
actions = {}
forward = (world_rest['headfront'].translation-world_rest['Head'].translation).normalized()
for role, (src, duration, looping) in CLIPS.items():
    action = bpy.data.actions.new('A_Mutant3_' + role)
    action.use_fake_user = True
    activate(rig, action)
    count = round(duration * FPS)
    scene.frame_start, scene.frame_end = 0, count
    previous, first, trajectory = {}, {}, []
    for frame in range(count+1):
        scene.frame_set(frame)
        t = frame/FPS
        phase = frame/count
        if role == 'PounceWindup':
            if t < .26:
                data = blend(idle_pose, crouch_pose, smooth(t/.26))
            elif t < .44:
                data = crouch_pose
            else:
                data = blend(crouch_pose, launch_pose, smooth((t-.44)/.16))
        elif role == 'PounceFlight':
            data = sample(src, .08 + phase*.52)
        elif role == 'PounceLand':
            data = sample(src, .60 + phase*1.65)
        else:
            data = sample(src, t)
        set_pose(data, src, role)
        if frame == 0:
            first = {pb.name: pb.matrix_basis.copy() for pb in ordered}
        seam = smooth((t-(duration-.05))/.05) if looping else 0
        for pb in ordered:
            if seam:
                pb.matrix_basis = pb.matrix_basis.lerp(first[pb.name], seam)
            q = pb.rotation_quaternion.copy()
            if pb.name in previous and previous[pb.name].dot(q) < 0:
                q.negate()
            pb.rotation_quaternion = q
            pb.scale = (1,1,1)
            previous[pb.name] = q.copy()
            for prop in ['location','rotation_quaternion','scale']:
                pb.keyframe_insert(prop, frame=frame, group=pb.name)
        bpy.context.view_layer.update()
        trajectory.append({n: list((rig.matrix_world @ rig.pose.bones[n].matrix).translation)
                           for n in ['Hips','LeftHand','RightHand','LeftFoot','RightFoot']})
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(OUT / (action.name+'.fbx')), use_selection=True,
        object_types={'ARMATURE','MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0, axis_forward='-Y', axis_up='Z',
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='STRIP')
    record = dict(source=src, seconds=duration, fps=FPS, loop=looping, frames=[0,count])
    if role in ['FeralRun','FeralSprint']:
        speeds = []
        for foot in ['LeftFoot','RightFoot']:
            floor = min(p[foot][2] for p in trajectory)
            for a,b in zip(trajectory,trajectory[1:]):
                speed = -(Vector(b[foot])-Vector(a[foot])).dot(forward)*FPS*100
                if max(a[foot][2],b[foot][2]) < floor+.045 and speed > 100:
                    speeds.append(speed)
        record['reference_speed_cms'] = round(statistics.median(speeds),1) if speeds else None
    if role.startswith('Claw'):
        record['hand_forward_peak_seconds'] = {hand: max(range(len(trajectory)),key=lambda i:Vector(trajectory[i][hand]).dot(forward))/FPS
                                               for hand in ['LeftHand','RightHand']}
    outputs[role] = record
    actions[role] = action
    (ROOT / ('trajectory_'+role+'.json')).write_text(json.dumps(trajectory), encoding='utf-8')
    print('AUTHORED '+role+' '+json.dumps(record), flush=True)

activate(rig, actions['FeralSprint'])
scene.frame_start, scene.frame_end = 0, round(CLIPS['FeralSprint'][1]*FPS)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Mutant3_Khaimera_Feral.blend'))
(ROOT / 'animation_contract.json').write_text(json.dumps(dict(
    source_url='https://www.fab.com/listings/e7c665c1-8c13-42f0-9152-0753008853d7',
    source='Epic Games Paragon Khaimera; UE licensed content; not open source',
    skeleton='/Game/Monsters/Mutant3Meshy/SK_Mutant3_Meshy_Skeleton', clips=outputs,
    state='Authored FBX; import pending; no runtime or visual acceptance performed'), indent=2), encoding='utf-8')
print('MUTANT3_FERAL_AUTHORING_COMPLETE', flush=True)
