import bpy,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\TacticalDevices20260913');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(p/'laser/seed_91803/textured_master_00001_.glb'));o=next(o for o in bpy.context.scene.objects if o.type=='MESH');vs=[o.matrix_world@v.co for v in o.data.vertices];print('ORIGINAL_WORLD_BOUNDS',[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(p/'laser/seed_91803/EditableMaster.blend'))
