"""Save the Hunyuan result as an editable source; no remesh or preview render."""
import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'flashlight_hunyuan.glb'))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Flashlight_Hunyuan_Editable.blend'))
print('HUNYUAN_EDITABLE_SOURCE_SAVED',flush=True)
