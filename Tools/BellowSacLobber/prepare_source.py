"""Archive the user's rigged GLB and read authoring inputs; no renders or tests."""
import json
import shutil
import hashlib
from pathlib import Path
import bpy

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012')
SOURCE = Path('C:/Users/allan/Downloads/Meshy_AI_Character_output.glb')
for sub in ('Source', 'Authoring', 'Exports', 'Textures', 'Records'):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
archived = ROOT / 'Source/BellowSacLobber_user_rig.glb'
if not archived.exists():
    shutil.copy2(SOURCE, archived)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(archived))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
          and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
from mathutils import Vector
points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
bounds = {'min': [min(p[a] for p in points) for a in range(3)],
          'max': [max(p[a] for p in points) for a in range(3)]}
rows = []
for b in rig.data.bones:
    rows.append({'name': b.name, 'parent': b.parent.name if b.parent else None,
                 'head': list(rig.matrix_world @ b.head_local),
                 'tail': list(rig.matrix_world @ b.tail_local), 'length': b.length})
weights = {}
for obj in meshes:
    for group in obj.vertex_groups:
        entries = [(v, e.weight) for v in obj.data.vertices for e in v.groups if e.group == group.index and e.weight > .05]
        if not entries:
            continue
        total = sum(w for v, w in entries)
        centroid = sum(((obj.matrix_world @ v.co) * w for v, w in entries), Vector()) / total
        weights[group.name] = {'vertices_above_005': len(entries), 'weighted_center': list(centroid)}
report = {'input': str(SOURCE), 'archived_source': str(archived),
          'sha256': hashlib.sha256(archived.read_bytes()).hexdigest(), 'bounds_blender_m': bounds,
          'rig': rig.name, 'rig_matrix': [list(row) for row in rig.matrix_world],
          'bones': rows, 'weighted_regions': weights,
          'meshes': [{'name': o.name, 'vertices': len(o.data.vertices),
                      'triangles': sum(len(p.vertices)-2 for p in o.data.polygons)} for o in meshes],
          'existing_actions': [a.name for a in bpy.data.actions]}
(ROOT / 'Records/source_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'Authoring/BellowSacLobber_source.blend'))
print('BELLOW_SOURCE ' + json.dumps(report), flush=True)
