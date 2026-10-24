"""Capture UV identities for topology correspondence, without changing assets."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
body = json.loads((WORK / 'FitInputs/player_body.json').read_text(encoding='utf-8-sig'))
modular = json.loads((WORK / 'FitInputs/modular_outfits.json').read_text(encoding='utf-8-sig'))
full = json.loads((WORK / 'full_body_receipt.json').read_text())['mesh']
paths = {'jason': modular['profiles'][body['body_mesh']]['native_bare_skin'], 'kaitlin': full}
for name, path in paths.items():
    asset = u.load_asset(path)
    dm, result = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot capture UV source: ' + path)
    _, triangles, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    vertex_uvs = {}
    for index, triangle in enumerate(triangles):
        a, b, c, valid = u.GeometryScript_MeshQueries.get_triangle_u_vs(dm, 0, index)
        if not valid:
            raise RuntimeError('Missing body UV data: ' + path)
        for vertex, uv in zip((triangle.x, triangle.y, triangle.z), (a, b, c)):
            vertex_uvs.setdefault(vertex, set()).add((round(uv.x, 6), round(uv.y, 6)))
    (WORK / (name + '_body_uv.json')).write_text(json.dumps({
        'source': path, 'vertex_uvs': {str(k): sorted(v) for k, v in vertex_uvs.items()}}, separators=(',', ':')), encoding='utf-8')
    print('KAITLIN_BODY_UV_CAPTURED', name, len(vertex_uvs), flush=True)
(WORK / 'capture_body_uv_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
