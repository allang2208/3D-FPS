"""Import a licensed Meshy export unchanged for source-motion inspection.

Run in background Blender with --source <FBX/GLB> --out <new directory>.
This creates a source .blend and inventory; it does not retarget or publish.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
source = args.source.resolve(strict=True)
out = args.out.resolve()
if source.suffix.lower() not in ('.fbx', '.glb'):
    raise ValueError('Use the complete FBX or GLB export, including its rig.')
if out.exists():
    raise FileExistsError('Choose a new output directory: ' + str(out))

bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix.lower() == '.fbx':
    bpy.ops.import_scene.fbx(filepath=str(source), use_anim=True,
                            automatic_bone_orientation=False)
else:
    bpy.ops.import_scene.gltf(filepath=str(source))

scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
rigs = [obj for obj in scene.objects if obj.type == 'ARMATURE']
if not rigs or not bpy.data.actions:
    raise ValueError('The export must contain both a skeleton and animation.')

def matrix_rows(matrix):
    return [list(row) for row in matrix]


inventory = {
    'source': str(source),
    'sha256': hashlib.file_digest(source.open('rb'), 'sha256').hexdigest(),
    'intended_source': 'Meshy Sit_Lie_Bed / action_id 371',
    'action_identity_verified': False,
    'status': 'source_import_only_requires_motion_review',
    'blender_version': bpy.app.version_string,
    'fps_after_import': fps,
    'scene_unit_scale': scene.unit_settings.scale_length,
    'retargeted': False,
    'published_to_game': False,
    'rigs': [],
    'actions': [],
    'meshes': [],
}
for rig in rigs:
    inventory['rigs'].append({
        'object': rig.name,
        'object_matrix': matrix_rows(rig.matrix_world),
        'active_action': (rig.animation_data.action.name
                          if rig.animation_data and rig.animation_data.action else None),
        'bones': [{
            'name': bone.name,
            'parent': bone.parent.name if bone.parent else None,
            'rest_matrix': matrix_rows(bone.matrix_local),
        } for bone in rig.data.bones],
    })
for action in bpy.data.actions:
    first, last = map(float, action.frame_range)
    inventory['actions'].append({
        'name': action.name,
        'frame_range': [first, last],
        'duration_seconds': (last - first) / fps,
        'slots': [slot.identifier for slot in action.slots],
    })
for obj in scene.objects:
    if obj.type == 'MESH':
        inventory['meshes'].append({
            'name': obj.name, 'vertices': len(obj.data.vertices),
            'armature': obj.find_armature().name if obj.find_armature() else None,
        })

out.mkdir(parents=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'source_unmodified.blend'))
(out / 'source_inventory.json').write_text(
    json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
print('MESHY_BED_SOURCE_IMPORTED', str(out), flush=True)
