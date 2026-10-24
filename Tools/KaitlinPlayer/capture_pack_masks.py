"""Read the existing bag/seam motion masks for female harness authoring."""
import gc
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
inventory = json.loads((WORK / 'FitInputs/inventory.json').read_text())
output = WORK / 'Backpacks'
output.mkdir(exist_ok=True)
mask_file = output / 'motion_masks.json'
data = json.loads(mask_file.read_text()) if mask_file.exists() else {}
for row in inventory['meshes']:
    if 'backpack' not in row['roles']:
        continue
    if row['source'] in data:
        continue
    asset = u.load_asset(row['source'])
    mesh, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read backpack seam source: ' + row['source'])
    _, colors, valid, gaps = u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(mesh, False)
    if not valid or gaps:
        raise RuntimeError('Backpack needs its authored seam mask: ' + row['source'])
    data[row['source']] = [color.r for color in u.GeometryScript_List.convert_color_list_to_array(colors)]
    del asset, mesh, colors
    gc.collect()
    u.SystemLibrary.collect_garbage()
(output / 'motion_masks.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
mounts = json.loads((WORK / 'FitInputs/player_body.json').read_text(encoding='utf-8-sig'))['outfits']
static_file = output / 'static_bodies.json'
statics = json.loads(static_file.read_text()) if static_file.exists() else {}
for mount in mounts.values():
    if 'rigid_pack' not in mount or 'hanging_pack' in mount:
        continue
    path = mount['rigid_pack']['mesh']
    if path in statics:
        continue
    asset = u.load_asset(path)
    mesh, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read rigid backpack body: ' + path)
    _, positions, _ = u.GeometryScript_MeshQueries.get_all_vertex_positions(mesh, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
    statics[path] = {'positions': [[point.x, point.y, point.z] for point in positions]}
    del asset, mesh, positions
    gc.collect()
    u.SystemLibrary.collect_garbage()
static_file.write_text(json.dumps(statics, separators=(',', ':')), encoding='utf-8')
(WORK / 'capture_pack_masks_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_PACK_MASKS_CAPTURED', len(data), flush=True)
import runpy
if not (WORK / 'ViewSkin/material_inputs.json').exists():
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/KaitlinPlayer/capture_skin_materials.py', run_name='__main__')
