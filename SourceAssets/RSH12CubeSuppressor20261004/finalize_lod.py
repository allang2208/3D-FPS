"""Finish authored LOD1 offline; live import_lod has deferred completion semantics."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use the offline authoring stage for final LOD import')
receipt = json.loads((O / 'import_receipt.json').read_text(encoding='utf8'))
auth = json.loads((O / 'authoring.json').read_text(encoding='utf8'))
mesh = u.load_asset(receipt['mesh'])
if not mesh:
    raise RuntimeError('Saved cube mesh missing')
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    if editor.import_lod(mesh, 1, auth['lod1_fbx']) != 1:
        raise RuntimeError('Authored cube LOD1 import failed')
    if not editor.set_lod_screen_sizes(mesh, [1., .12]):
        raise RuntimeError('Cube LOD screen-size assignment failed')
    slots = list(mesh.static_materials)
    for i, slot in enumerate(slots):
        slot.material_interface = u.load_asset(receipt['slots'][str(slot.material_slot_name)])
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Could not save cube with LOD1')
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))
receipt['lod1_saved'] = True
(O / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print('RSH_CUBE_LOD1_SAVED', mesh.get_path_name())
