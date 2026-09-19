"""Compare bone hierarchies of the old and new viewmodel FBX exports.

Blender --background --python <this> -- <old.fbx> <new.fbx> <out.json>
Read-only diagnostic: the skeleton saved for UE must match the hierarchy the five
animation clips were authored against.
"""
import bpy
import json
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
old, new, out = Path(args[0]), Path(args[1]), Path(args[2])


def bones(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    armatures = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    result = {}
    for armature in armatures:
        result[armature.name] = [[b.name, b.parent.name if b.parent else None] for b in armature.data.bones]
    return result


old_bones = bones(old)
new_bones = bones(new)
report = {'old_armatures': {k: len(v) for k, v in old_bones.items()},
          'new_armatures': {k: len(v) for k, v in new_bones.items()}}
old_first = next(iter(old_bones.values()))
new_first = next(iter(new_bones.values()))
report['identical'] = old_first == new_first
if old_first != new_first:
    old_names = [n for n, _ in old_first]
    new_names = [n for n, _ in new_first]
    report['name_diff'] = {'only_old': [n for n in old_names if n not in new_names],
                           'only_new': [n for n in new_names if n not in old_names],
                           'same_order': old_names == new_names}
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))