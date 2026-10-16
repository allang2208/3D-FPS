import bpy,json
from pathlib import Path
O=Path(__file__).parent;R=json.loads((O/'install_receipt.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=R['export'])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Final/M16_M4Stock_Editable.blend'))
print('M16_M4_STOCK_EDITABLE_SAVED',flush=True)
