import bpy,json
from pathlib import Path
O=Path(__file__).parent;R=json.loads((O/'install_receipt.json').read_text())
for key,row in R['meshes'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 bpy.ops.import_scene.fbx(filepath=row['export'])
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'Final'/(key+'_Editable.blend')))
 print('EDITABLE_SAVED',key,flush=True)
