"""Extract the held-object sway signal from a Kimodo GLB: chest pose deltas per frame.

Blender --background --python <this> -- <glb> <out.json> <frames>
Read-only. The character holds something with both hands steady, so the chest's world motion
in the clip is exactly the ambient sway we want to re-apply to a first-person held tool.
Kimodo output is Z-up after glTF import, character forward is -Y, 30 fps.
"""
import bpy
import json
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
glb = Path(args[0])
out = Path(args[1])
frames = int(args[2]) if len(args) > 2 else 90

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
scene = bpy.context.scene
armature = next(o for o in scene.objects if o.type == 'ARMATURE')

samples = []
for frame in range(frames):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    entry = {'frame': frame}
    for name in ['Hips', 'Chest', 'Head']:
        bone = armature.pose.bones.get(name)
        world = armature.matrix_world @ bone.matrix
        quaternion = world.to_quaternion()
        entry[name] = {
            'pos': [round(v, 5) for v in world.translation],
            'quat': [round(v, 6) for v in (quaternion.w, quaternion.x, quaternion.y, quaternion.z)],
        }
    samples.append(entry)

report = {'source': str(glb), 'frames': frames, 'fps': 30, 'samples': samples}
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('EXTRACTED', len(samples), 'frames')
for name in ['Hips', 'Chest', 'Head']:
    xs = [s[name]['pos'][0] for s in samples]
    ys = [s[name]['pos'][1] for s in samples]
    zs = [s[name]['pos'][2] for s in samples]
    print(f'{name}: x range {max(xs)-min(xs):.4f} y range {max(ys)-min(ys):.4f} z range {max(zs)-min(zs):.4f}')