# Flip imported Y back to the live riser and restore the original envelope.
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PATH = '/Game/Weapons/DarkBow20260925/RiserDetail20260925/SM_DarkBow_RiserDetail'
TARGET = {'size': (38.223, 3.511, 139.999), 'origin_y': -0.935}
mesh = u.load_asset(PATH)
if mesh is None:
    raise RuntimeError('missing refined riser')

def info():
    b = mesh.get_bounds()
    return {
        'extent': [b.box_extent.x, b.box_extent.y, b.box_extent.z],
        'origin': [b.origin.x, b.origin.y, b.origin.z],
        'size': [b.box_extent.x * 2, b.box_extent.y * 2, b.box_extent.z * 2],
    }

def write(dm):
    options = u.GeometryScriptCopyMeshToAssetOptions()
    options.set_editor_property('enable_recompute_normals', False)
    options.set_editor_property('enable_recompute_tangents', True)
    options.set_editor_property('replace_materials', False)
    _, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
        dm, mesh, options, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('write failed')

before = info()
dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if outcome != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('read failed')
# Importer mirrored Y (origin +0.935 vs live -0.935). Flip around the grip origin.
u.GeometryScript_MeshTransforms.scale_mesh(dm, u.Vector(1, -1, 1), u.Vector(0, 0, 0), True)
write(dm)
flipped = info()
sx = TARGET['size'][0] / flipped['size'][0]
sy = TARGET['size'][1] / flipped['size'][1]
sz = TARGET['size'][2] / flipped['size'][2]
dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
u.GeometryScript_MeshTransforms.scale_mesh(dm, u.Vector(sx, sy, sz), u.Vector(0, 0, 0), True)
write(dm)
after = info()
mesh.modify()
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_package()], False):
    raise RuntimeError('save failed')
if after['origin'][1] > 0:
    raise RuntimeError('Y still flipped: ' + str(after))
if abs(after['size'][1] - TARGET['size'][1]) > 0.08:
    raise RuntimeError('thickness mismatch: ' + str(after))
receipt = {
    'before': {k: [round(x, 3) for x in v] for k, v in before.items()},
    'flipped': {k: [round(x, 3) for x in v] for k, v in flipped.items()},
    'after': {k: [round(x, 3) for x in v] for k, v in after.items()},
    'scale': [round(sx, 5), round(sy, 5), round(sz, 5)],
    'runtime_tested': False,
}
(HERE / 'axis_fix_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BOW_RISER_AXIS_FIXED', json.dumps(receipt), flush=True)
