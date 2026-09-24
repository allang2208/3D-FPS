"""Production input: extract flat water outlines from the two saved source meshes."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/WaterImpactAll20260924'
OUT.mkdir(exist_ok=True)
assets = [
    '/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterWaves',
    '/Game/Dungeons/AtmosphereV2/GateWater/Meshes/SM_Dungeon_ShallowPuddles',
]
# Use the authored name, rather than guessing from the level actor label.
manifest = json.loads((ROOT / 'SourceAssets/DungeonGateWater20260922/Authored/manifest.json').read_text())
assets[1] = '/Game/Dungeons/AtmosphereV2/GateWater/Meshes/' + next(x['name'] for x in manifest['meshes'] if not x['collision'])
result = []
for path in assets:
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing water mesh ' + path)
    lod = u.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, u.new_object(u.DynamicMesh), u.GeometryScriptCopyMeshFromAssetOptions(), lod)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read water source mesh ' + path)
    dm, vs, _ = u.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    verts = [tuple(round(a, 3) for a in v.to_tuple()) for v in u.GeometryScript_List.convert_vector_list_to_array(vs)]
    dm, ts, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, True)
    planes = defaultdict(Counter)
    for tri in u.GeometryScript_List.convert_triangle_list_to_array(ts):
        a, b, c = [verts[i] for i in tri.to_tuple()]
        if max(a[2], b[2], c[2]) - min(a[2], b[2], c[2]) > .01:
            continue
        if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) < .0001:
            continue
        for p, q in ((a, b), (b, c), (c, a)):
            planes[round(a[2], 2)][tuple(sorted((p[:2], q[:2])))] += 1
    patches, last_z = [], None
    for z in sorted(planes, reverse=True):
        # Fountain discs have a 6 cm bottom face: only the top is an entry surface.
        if last_z is not None and last_z - z < 10:
            continue
        last_z = z
        edges = {edge for edge, count in planes[z].items() if count == 1}
        while edges:
            start, current = edges.pop()
            polygon = [start, current]
            while current != start:
                match = next((edge for edge in edges if current in edge), None)
                if match is None:
                    raise RuntimeError('Open water outline ' + path)
                edges.remove(match)
                current = match[1] if match[0] == current else match[0]
                if current != start:
                    polygon.append(current)
            if len(polygon) >= 3:
                patches.append(dict(z=z, polygon=polygon))
    materials = [mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property('static_materials')))]
    result.append(dict(mesh=mesh.get_path_name(), materials=materials, patches=patches))
(OUT / 'water-footprints.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WATER_FOOTPRINTS_EXPORTED ' + json.dumps([dict(mesh=r['mesh'], materials=r['materials'], patches=len(r['patches']), vertices=[len(p['polygon']) for p in r['patches']]) for r in result]))
