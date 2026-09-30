import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'SK_LMG201_Chainmail_ADS34.fbx'))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Chainmail_ADS34_Editable.blend'))
