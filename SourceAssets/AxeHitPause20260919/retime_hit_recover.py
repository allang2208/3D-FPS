"""Retime the accepted thumb-fixed recovery: hold, lever, extract, return.

Blender --background --python <this>. Only HitRecover is exported; no renders/tests.
The runtime still maps the 0.44-second source clip onto 0.92 seconds.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'SourceAssets/AxeThumb20260919/Fixed/Axe_ThumbFix_Attack_Editable.blend'
FPS = 300
SOURCE_SECONDS = .44
RUNTIME_SECONDS = .92
HOLD_END = .20
PRY_START = .23
EXTRACT_END = .64
NAME = 'A_Harvest_Axe_HitRecover'
(HERE / 'Export').mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
original = bpy.data.actions[NAME]
rig.animation_data.action = original
rig.animation_data.action_slot = original.slots[0]
scene.render.fps = FPS
scene.render.fps_base = 1
scene.frame_start = 0
scene.frame_end = round(SOURCE_SECONDS * FPS)

def read_pose(old_age):
    f = old_age / RUNTIME_SECONDS * SOURCE_SECONDS * FPS
    scene.frame_set(math.floor(f), subframe=f - math.floor(f))
    return {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}

def blend_pose(a, b, amount):
    u = amount**3 * (amount * (6 * amount - 15) + 10)
    result = {}
    for name in a:
        pa, qa, sa = a[name].decompose()
        pb, qb, sb = b[name].decompose()
        result[name] = Matrix.LocRotScale(pa.lerp(pb, u), qa.slerp(qb, u), sa.lerp(sb, u))
    return result

contact = read_pose(0)
pry_entry = read_pose(.15)
samples = []
for frame in range(scene.frame_end + 1):
    age = RUNTIME_SECONDS * frame / scene.frame_end
    if age <= HOLD_END:
        pose = contact
    elif age < PRY_START:
        # Blend directly into the established braced pose, skipping the old
        # 75-150 ms high-frequency micro-recoil before the deliberate lever motion.
        pose = blend_pose(contact, pry_entry, (age - HOLD_END) / (PRY_START - HOLD_END))
    else:
        old_age = age - .08 if age <= EXTRACT_END else .56 + (age - EXTRACT_END) * (.36 / .28)
        pose = read_pose(old_age)
    samples.append(pose)

original.name = 'REF_ThumbFix_BeforePause_' + NAME
original.use_fake_user = True
action = bpy.data.actions.new(NAME)
action.use_fake_user = True
rig.animation_data.action = action
previous = {}
for frame, pose in enumerate(samples):
    scene.frame_set(frame)
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = pose[bone.name]
        q = bone.rotation_quaternion.copy()
        if bone.name in previous and q.dot(previous[bone.name]) < 0:
            q.negate()
        bone.rotation_quaternion = q
        previous[bone.name] = q.copy()
        for channel in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(channel, frame=frame, group=bone.name)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'

bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx = HERE / 'Export' / (NAME + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                        bake_anim_simplify_factor=0)
scene.frame_set(0)
blend = HERE / 'Axe_HitPause_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report = {
    'revision': 'H4_V5_ThumbFix1_HitPause200ms',
    'source': str(SOURCE), 'blend': str(blend), 'fbx': str(fbx), 'fps': FPS,
    'source_seconds': SOURCE_SECONDS, 'runtime_seconds': RUNTIME_SECONDS,
    'phase_seconds_after_contact': {'hold_end': HOLD_END, 'pry_start': PRY_START,
                                    'pry_end': .51, 'extract_end': EXTRACT_END, 'return_end': .92},
    'runtime_tested': False, 'rendered': False,
}
(HERE / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('AXE_HIT_PAUSE_EXPORTED', fbx, flush=True)
