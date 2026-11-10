"""Bake flame attachment cross-sections from the installed blade module geometry.
Read-only Unreal geometry access; writes C++ author data, never runs a world.
"""
import bisect
import json
from pathlib import Path
import unreal as u
from write_surface_header import write

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
G, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List


def paths(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from paths(v)
    elif isinstance(value, list):
        for v in value:
            yield from paths(v)
    elif isinstance(value, str) and value.startswith('/Game/') and '/SM_' in value:
        yield value


def profile(path, axis=2, crop=(.055, .97), skeletal=False):
    mesh = u.load_asset(path)
    if not isinstance(mesh, u.SkeletalMesh if skeletal else u.StaticMesh):
        raise RuntimeError('Missing blade mesh: ' + path)
    copy = G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
    dm, outcome = copy(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(),
        u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL if skeletal else u.GeometryScriptLODType.RENDER_DATA, lod_index=0))
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot extract blade silhouette: ' + path)
    _, points, _ = Q.get_all_vertex_positions(dm, False)
    _, faces, _ = Q.get_all_triangle_indices(dm, False)
    side, normal = (axis+1)%3, (axis+2)%3
    points = L.convert_vector_list_to_array(points)
    retained = None
    if skeletal:
        B = u.GeometryScript_BoneWeights
        _, bones = B.get_all_bones_info(dm)
        bone = next(b for b in bones if str(b.name) == 'WPN_root')
        retained = set()
        for i in range(len(points)):
            _, weights, _ = B.get_vertex_bone_weights(dm, i)
            if any(w.bone_index == bone.index and w.weight > .99 for w in weights):
                retained.add(i)
        points = [bone.world_transform.inverse_transform_location(p) for p in points]
    points = [tuple((p.x, p.y, p.z)[c] for c in (side, normal, axis)) for p in points]
    faces = [(int(f.x), int(f.y), int(f.z)) for f in L.convert_triangle_list_to_array(faces)]
    if retained is not None:
        faces = [f for f in faces if all(i in retained for i in f)]
    surface_points = [points[i] for i in retained] if retained is not None else points
    zmin, zmax = min(p[2] for p in surface_points), max(p[2] for p in surface_points)
    # Exclude blade-module collars/root seams. The carrier is only the installed
    # blade/head module, so grips, tassels and handles never become emitters.
    start, end = zmin + crop[0]*(zmax-zmin), zmin + crop[1]*(zmax-zmin)
    if skeletal:
        # Native shovel author puts the spade below z=0 and the hand shaft above
        # it in WPN_root space. Read only the actual rigid spade triangles.
        start, end = zmin*.985, min(0., zmax)-.002
    heights = [start+(end-start)*i/7 for i in range(8)]
    samples = [[] for _ in heights]
    for triangle in faces:
        for ia, ib in ((0, 1), (1, 2), (2, 0)):
            a, b = points[triangle[ia]], points[triangle[ib]]
            if a[2] > b[2]:
                a, b = b, a
            if b[2]-a[2] < 1.e-6:
                continue
            first, last = bisect.bisect_left(heights, a[2]), bisect.bisect_right(heights, b[2])
            for i in range(first, last):
                t = (heights[i]-a[2])/(b[2]-a[2])
                samples[i].append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
    sections = []
    for i, sample in enumerate(samples):
        if not sample:
            raise RuntimeError(f'Empty blade section {i}: {path}')
        lo = [min(p[c] for p in sample) for c in (0, 1)]
        hi = [max(p[c] for p in sample) for c in (0, 1)]
        sections.append([(lo[c]+hi[c])*.5 for c in (0, 1)]+[max(.0008 if skeletal else .08, (hi[c]-lo[c])*.5) for c in (0, 1)])
    return dict(mesh=mesh.get_path_name(), axis=axis, start=start, end=end, sections=sections)


def run():
    meshes = set()
    catalogs = {}
    for f in (ROOT/'Content/ColdSteelData').glob('*modules.json'):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        blade = data.get('slots', {}).get('blade_1', {})
        if blade:
            found = sorted(set(paths(blade)))
            catalogs[f.name] = found
            meshes.update(found)
    rows = [profile(path) for path in sorted(meshes)]
    tools = json.loads((ROOT/'Content/ColdSteelData/production_tools.json').read_text(encoding='utf-8-sig'))
    rows.append(profile(tools['tool_shovel']['tool_mesh'], 0, (.69, .985)))
    rows.append(profile(tools['tool_shovel']['tool_viewmodel'], skeletal=True))
    write(rows)
    receipt = dict(catalogs=catalogs, profiles=rows, source='installed render LOD0 triangles',
        pie_running=False if '-run=' in u.SystemLibrary.get_command_line().lower() else u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), runtime_tested=False)
    (OUT/'surface-profiles.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('FLAME_ARMOR_SURFACE_PROFILES', len(rows), 'catalogs', len(catalogs), 'PIE', receipt['pie_running'])


if __name__ == '__main__':
    run()
