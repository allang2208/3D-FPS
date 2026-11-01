import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
asset = '/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x'
mesh = u.load_asset(asset)
if not mesh:
    raise RuntimeError('M24 factory optic is unavailable')

# Bounds center of the existing upper glass, in Blender source metres.
# The native M24 export maps (x, y, z) to UE (x, -y, z) centimetres.
geometry = json.loads((O / 'top_geometry.json').read_text())
top = geometry['M24_TopGlass_Lowpoly']
center = [(lo + hi) * .5 for lo, hi in zip(top['min'], top['max'])]
rear = [center[0] * 100, -center[1] * 100, center[2] * 100]
sockets = {
    'TopSightRear': rear,
    'TopSightFront': [rear[0], rear[1] - 10, rear[2]],
    'TopSightUp': [rear[0], rear[1], rear[2] + 1],
}
backup = O / 'Backups'
backup.mkdir(exist_ok=True)
disk = Path(u.Paths.project_content_dir()) / 'Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x.uasset'
saved_backup = backup / disk.name
if not saved_backup.exists():
    shutil.copy2(disk, saved_backup)
with u.ScopedEditorTransaction('M24 upper 1x sight alignment sockets'):
    mesh.modify()
    for name, location in sockets.items():
        socket = mesh.find_socket(name)
        if not socket:
            socket = u.StaticMeshSocket(outer=mesh)
            socket.set_editor_property('socket_name', name)
            mesh.add_socket(socket)
        socket.set_editor_property('relative_location', u.Vector(*location))
        socket.set_editor_property('relative_rotation', u.Rotator())
        socket.set_editor_property('relative_scale', u.Vector(1, 1, 1))
if not u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
    raise RuntimeError('M24 scope could not be saved')
receipt = {'saved_asset': asset, 'upper_sockets_cm': sockets,
           'geometry_and_materials': 'retained', 'runtime_tested': False}
(O / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('M24_DUAL_OPTIC_SAVED', json.dumps(receipt), flush=True)
