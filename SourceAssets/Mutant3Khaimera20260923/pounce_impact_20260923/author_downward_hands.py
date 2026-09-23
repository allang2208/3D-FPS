"""Author wrist/finger rotations over the accepted coherent pounce, without arm IK."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT = Path(__file__).parent
SOURCE = ROOT.parent/'pounce_arm_refine'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Mutant3_Pounce_ReferenceRake.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.fps = 60
scene.render.fps_base = 1
roles = ['PounceFlight', 'PounceLand']
digits = ['Index', 'Middle', 'Ring', 'Pinky', 'Thumb']
sides = ['Left', 'Right']
names = [side+'Hand' for side in sides]+[
    f'{side}{digit}{joint}_Claw' for side in sides for digit in digits for joint in range(1,4)]
contract = json.loads((SOURCE/'animation_contract.json').read_text())
contract['clips'] = {role: contract['clips'][role] for role in roles}
originals = {role: bpy.data.actions['A_Mutant3_'+role] for role in roles}
rig_rotation = rig.matrix_world.to_quaternion()
chains = json.loads((ROOT.parent/'claw_reference_20260923/claw_skin.json').read_text())['chains']

def activate(action):
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute = True

def smooth(start, end, value):
    t = max(0.0, min(1.0, (value-start)/(end-start)))
    return t*t*(3.0-2.0*t)

def weight(role, seconds):
    # Zero at flight entry; identical full weight across flight/landing; ease
    # back to the untouched recovery pose before the landing clip ends.
    return smooth(.18, .42, seconds) if role == 'PounceFlight' else 1.0-smooth(.10, .58, seconds)

curl_axes = {}
for key, chain in chains.items():
    direction = (Vector(chain['knots_world'][-1])-Vector(chain['knots_world'][0])).normalized()
    curl = Vector((0,.8,-.6)).normalized() if key.endswith('Thumb') else Vector((0,0,-1))
    axis = direction.cross(curl).normalized()
    for name in chain['bones']:
        rest_rotation = (rig.matrix_world @ rig.data.bones[name].matrix_local).to_quaternion()
        curl_axes[name] = rest_rotation.inverted() @ axis

authored = {}
for role in roles:
    activate(originals[role])
    frames = contract['clips'][role]['frames'][1]
    # Cache before authoring so each frame starts from the accepted pose.
    baseline = []
    for frame in range(frames+1):
        scene.frame_set(frame)
        baseline.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in names})
    poses = []
    for frame in range(frames+1):
        scene.frame_set(frame)
        amount = weight(role, frame/60.0)
        for name in names:
            rig.pose.bones[name].rotation_quaternion = baseline[frame][name]
        # Keep the open, splayed claw. Small PIP/DIP flex adds a rake without
        # closing the fingers into the old weapon-gripping fist.
        for side in sides:
            for digit in digits:
                angles = (0, 3, 2) if digit == 'Thumb' else (0, 6, 4)
                for joint, degrees in enumerate(angles, 1):
                    name = f'{side}{digit}{joint}_Claw'
                    rig.pose.bones[name].rotation_quaternion = baseline[frame][name] @ Quaternion(
                        curl_axes[name], math.radians(degrees)*amount)
        bpy.context.view_layer.update()
        for side in sides:
            hand = rig.pose.bones[side+'Hand']
            tips = [((rig.matrix_world @ rig.pose.bones[side+digit+'3_Claw'].matrix).to_quaternion()
                     @ Vector((0,1,0))).normalized() for digit in digits[:4]]
            tip = sum(tips, Vector()).normalized()
            # Minimal swing toward gravity; no arbitrary wrist roll and no
            # shoulder/elbow override. Cap wrist correction at 55 degrees.
            down = Vector((0,0,-1))
            axis = tip.cross(down)
            if amount > 0 and axis.length > 1e-6:
                angle = min(math.radians(55), tip.angle(down))*amount
                delta = Quaternion(axis.normalized(), angle)
                world = (rig.matrix_world @ hand.matrix).to_quaternion()
                local_delta = world.inverted() @ delta @ world
                hand.rotation_quaternion = (baseline[frame][side+'Hand'] @ local_delta).normalized()
        bpy.context.view_layer.update()
        poses.append({name: rig.pose.bones[name].rotation_quaternion.copy() for name in names})
    authored[role] = poses

out = ROOT/'animations'
out.mkdir(exist_ok=True)
for role in roles:
    original = originals[role]
    original.name = 'BeforeDownwardHands_'+original.name
    action = original.copy()
    action.name = 'A_Mutant3_'+role
    action.use_fake_user = True
    activate(action)
    scene.frame_start, scene.frame_end = contract['clips'][role]['frames']
    previous = {}
    for frame, pose in enumerate(authored[role]):
        scene.frame_set(frame)
        for name, value in pose.items():
            q = value.copy()
            if name in previous and q.dot(previous[name]) < 0: q.negate()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = q
            bone.keyframe_insert('rotation_quaternion', frame=frame, group=name)
            previous[name] = q.copy()
    selected_paths = {f'pose.bones["{name}"].rotation_quaternion' for name in names}
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path in selected_paths:
                        for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers):
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(out/(action.name+'.fbx')), use_selection=True,
        object_types={'ARMATURE','MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True)
    print('POUNCE_HANDS_EXPORTED '+role, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Pounce_DownwardHands.blend'))
contract.update({
    'revision': 'Only wrists and finger rotations; downward swing over accepted coherent arm chain',
    'state': 'Two hand animation sources authored; selective UE hand-track installation pending',
    'rotation_tracks': names,
    'wrist_swing_cap_degrees': 55,
    'finger_extra_curl_degrees': [0,6,4],
    'thumb_extra_curl_degrees': [0,3,2],
    'hand_weight': {'flight_ramp_seconds': [.18,.42], 'land_release_seconds': [.10,.58]},
    'install': 'Copy only these 32 bone rotation tracks; keep existing translations, scales and all other tracks',
})
for obsolete in ['arm_bones','source_arm_times_seconds','source_native_downstroke_seconds','flight_downstroke_seconds']:
    contract.pop(obsolete, None)
(ROOT/'animation_contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
print('POUNCE_DOWNWARD_HANDS_AUTHORED', flush=True)
