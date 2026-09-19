"""Inspect a Kimodo GLB: per-frame joint positions and a multi-view render sheet.

Blender --background --python <this> -- <glb> <out_dir> [frames]
Diagnostic only: the GLB carries a 30-joint SOMA skeleton, no character mesh.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
glb = Path(args[0])
out = Path(args[1])
out.mkdir(parents=True, exist_ok=True)
sample_frames = [int(v) for v in args[2].split(',')] if len(args) > 2 else [0, 22, 45, 67, 89]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
scene = bpy.context.scene

armature = next(o for o in scene.objects if o.type == 'ARMATURE')
print('ARMATURE', armature.name, 'bones', len(armature.data.bones))
print('BONE_NAMES', [b.name for b in armature.data.bones])

# Key joint world positions across the clip: is the motion a plausible idle?
report = {'bones': [b.name for b in armature.data.bones], 'frames': {}}
for frame in sample_frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    entry = {}
    for name in ['Hips', 'Chest', 'Head', 'LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm']:
        bone = armature.pose.bones.get(name)
        if bone:
            world = armature.matrix_world @ bone.matrix
            entry[name] = [round(v, 4) for v in world.translation]
    report['frames'][frame] = entry
print(json.dumps(report, indent=2))

# Render sheet: front and side for each sampled frame, driven by the GLB's own skin.
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'SINGLE'
scene.display.shading.single_color = (0.55, 0.55, 0.58)
scene.render.resolution_x = 460
scene.render.resolution_y = 640
scene.render.film_transparent = False
camera_data = bpy.data.cameras.new('Kimodo')
camera = bpy.data.objects.new('Kimodo', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 2.2

# The GLB is Y-up; Blender imports it Z-up. Head +Y is the character's facing here.
views = {'front': ((0, -3.0, 1.0), (math.radians(90), 0, 0)),
         'side': ((3.0, 0, 1.0), (math.radians(90), 0, math.radians(90)))}
for name, (location, rotation) in views.items():
    camera.location = location
    camera.rotation_euler = rotation
    for frame in sample_frames:
        scene.frame_set(frame)
        scene.render.filepath = str(out / f'{name}_f{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
(out / 'kimodo_inspect.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KIMODO_INSPECT_DONE')