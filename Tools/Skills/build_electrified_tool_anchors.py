"""Derive enchantment anchors from the two existing tools; no preview or game.

Geometry Script reads rigid weapon vertices in the imported mesh's own reference
frame, so anchors do not depend on Blender/FBX bone-axis conventions.
Use mcp_call_codex.ps1 -PythonScript when the editor is already open.
"""
import json
from pathlib import Path
import unreal as u

PATHS = [
    '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe',
    '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe',
]
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(PATHS):
    raise RuntimeError('Preserve unsaved tool edits: ' + ', '.join(dirty.intersection(PATHS)))
saved = {}
for kind, path in zip(('axe', 'pickaxe'), PATHS):
    mesh = u.load_asset(path)
    dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot derive tool geometry: ' + path)
    _, valid, bone = u.GeometryScript_BoneWeights.get_bone_info(dynamic, 'WPN_root')
    if not valid:
        raise RuntimeError('Missing tool root: ' + path)
    points = []
    for vertex in range(u.GeometryScript_MeshQueries.get_num_vertex_i_ds(dynamic)):
        _, weight, valid = u.GeometryScript_BoneWeights.get_largest_vertex_bone_weight(dynamic, vertex)
        if not valid or weight.bone_index != bone.index:
            continue
        position, valid = u.GeometryScript_MeshQueries.get_vertex_position(dynamic, vertex)
        if valid:
            local = u.MathLibrary.inverse_transform_location(bone.world_transform, position)
            points.append((local.x, local.y, local.z))
    if len(points) < 10:
        raise RuntimeError('No rigid tool vertices: ' + path)
    def bounds(ps):
        return ([min(p[i] for p in ps) for i in range(3)], [max(p[i] for p in ps) for i in range(3)])
    lo, hi = bounds(points)
    axis = max(range(3), key=lambda i: hi[i]-lo[i])
    sides = [i for i in range(3) if i != axis]
    low = [p for p in points if p[axis] < lo[axis]+(hi[axis]-lo[axis])*.25]
    high = [p for p in points if p[axis] > hi[axis]-(hi[axis]-lo[axis])*.25]
    def width(ps):
        a, b = bounds(ps)
        return max(b[i]-a[i] for i in sides)
    head = max([low, high], key=width)
    a, b = bounds(head)
    across = max(sides, key=lambda i: b[i]-a[i])
    # Bind transforms may carry the FBX unit scale. Use relative widths in bone
    # space; a hard centimetre minimum here would collapse both ends together.
    band = max(1e-5, (b[across]-a[across])*.07)
    ends = [[p for p in head if p[across] <= a[across]+band],
            [p for p in head if p[across] >= b[across]-band]]
    anchors = []
    for vertices in ends:
        center = [sum(p[i] for p in vertices)/len(vertices) for i in range(3)]
        anchors.append(center)
    saved[kind] = {'asset': path, 'bone': 'WPN_root', 'base_local': anchors[0], 'tip_local': anchors[1], 'source_vertices': len(points)}
out = Path(u.Paths.project_content_dir())/'ColdSteelData/electrified-tool-anchors.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(saved, indent=2), encoding='utf-8')
print(json.dumps({'saved': saved, 'runtime_tested': False}))
