"""Export the installed mesh for targeted shell UV diagnosis; no asset changes."""
from pathlib import Path
import unreal as u
O = Path(__file__).parent
t = u.AssetExportTask()
t.object = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
t.filename = str(O / 'Installed_Super90.fbx')
t.automated = True
t.prompt = False
t.replace_identical = True
t.options = u.FbxExportOption()
t.options.set_editor_property('level_of_detail', False)
if not u.Exporter.run_asset_export_task(t):
    raise RuntimeError(str(t.errors))
print('SHELL_DIAGNOSIS_MESH_EXPORTED', t.filename)
