"""Author a continuous rear-hinge opening on the migrated rig, without rendering."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Quaternion

HERE = Path(__file__).parent
OUT = HERE / 'Authored'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'GamedevTreasureChest_UE.blend'))
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
scene.frame_start, scene.frame_end = 1, 31
arm = bpy.data.objects['GamedevTreasureChestRig']
mesh = bpy.data.objects['SK_GamedevTreasureChest']
arm.animation_data_clear()
lid = arm.pose.bones['Lid']
lid.rotation_mode = 'QUATERNION'
axis = arm.data.bones['Lid'].matrix_local.to_3x3().inverted() @ Vector((0, 1, 0))

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3.0-2.0*t)

# Keep the base planted. Brief release, weighted lift, then a small stop recoil.
for frame in range(1, 32):
    t = (frame-1)/30.0
    angle = 60.0*smooth((t-.08)/.70) if t <= .78 else 60.0-2.0*smooth((t-.78)/.22)
    lid.rotation_quaternion = Quaternion(axis, -math.radians(angle))
    lid.keyframe_insert(data_path='rotation_quaternion', frame=frame)
action = arm.animation_data.action
action.name = 'A_TreasureChest_Opening'
action.use_fake_user = True
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
scene.frame_set(1)
bpy.ops.export_scene.fbx(
    filepath=str(OUT / 'A_TreasureChest_Opening.fbx'), use_selection=True,
    object_types={'MESH', 'ARMATURE'}, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL', axis_forward='-Y', axis_up='Z',
    mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0.0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GamedevTreasureChest_Opening.blend'))
record = dict(clip=action.name, frames=31, fps=30, duration_seconds=1.0,
              looping=False, final_angle_degrees=58, peak_angle_degrees=60,
              source_reference='Original closed/open artwork and rear-hinge model; original runtime uses sprite fades.',
              motion='New 3D reconstruction: 0.08s release, 0.70s lift, 0.22s settle.',
              rendered=False, tested=False)
(HERE / 'opening_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('TREASURE_OPENING_EXPORTED ' + json.dumps(record))
