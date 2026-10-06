"""Read current asset triangles and reference bones for exact mount reconstruction."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
ROOT = '/Game/Weapons/G18/Integrated20260929'
Q = u.GeometryScript_MeshQueries


def xyz(v):
    return [v.x, v.y, v.z]


def matrix(t):
    origin = t.transform_location(u.Vector())
    cols = []
    for axis in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1)):
        p = t.transform_location(axis)
        cols.append([p.x - origin.x, p.y - origin.y, p.z - origin.z])
    return [[cols[c][r] for c in range(3)] + [xyz(origin)[r]] for r in range(3)] + [[0, 0, 0, 1]]


for name, path, skeletal in (
    ('host', ROOT + '/Single/SK_G18_Manny', True),
    ('holographic', ROOT + '/Attachments/SM_G18_holographic', False),
):
    asset = u.load_asset(path)
    copy = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh if skeletal else u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh
    mesh, status = copy(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read current mesh geometry ' + path)
    _, positions, _ = Q.get_all_vertex_positions(mesh, False)
    _, triangles, _ = Q.get_all_triangle_indices(mesh, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    slots = asset.materials if skeletal else asset.static_materials
    data = {'asset': path, 'vertices_cm': [xyz(v) for v in positions],
            'triangles': [xyz(t) for t in triangles],
            'slots': [str(s.material_slot_name) for s in slots],
            'material_paths': [s.material_interface.get_path_name() for s in slots],
            'materials': [u.GeometryScript_Materials.get_triangle_material_id(mesh, i)[0] for i in range(len(triangles))]}
    if skeletal:
        modifier = u.SkeletonModifier()
        modifier.set_skeletal_mesh(asset)
        data['reference'] = {bone: matrix(modifier.get_bone_transform(bone, True))
                             for bone in ('WPN_root', 'WPN_Slide', 'WPN_RearSight', 'WPN_FrontSight')}
    (O / (name + '_geometry.json')).write_text(json.dumps(data), encoding='utf8')
    print(name, len(positions), len(triangles), data['slots'], flush=True)
print('G18_MOUNT_GEOMETRY_READ', flush=True)
