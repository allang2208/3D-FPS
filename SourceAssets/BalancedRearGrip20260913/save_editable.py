import bpy,sys
from pathlib import Path
P=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
for seed in [91703,91727]:
    folder=P/f'seed_{seed}'
    if not (folder/'textured_master_00001_.glb').exists() or (folder/'BalancedRearGrip_Editable.blend').exists():continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(folder/'textured_master_00001_.glb'))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'BalancedRearGrip_Editable.blend'))
print('BALANCED_EDITABLE_SAVED',flush=True)
