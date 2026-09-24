import bpy, json
from pathlib import Path
GLB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ChestRitual20260909\warehouse_chest_ritual_v8.glb')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue
    loc = obj.bound_box
    xs=[c[0] for c in loc]; ys=[c[1] for c in loc]; zs=[c[2] for c in loc]
    print('PROBE', obj.name, 'scale', tuple(obj.scale), 'local_dims', [round(max(a)-min(a),4) for a in (xs,ys,zs)], 'obj_dims', [round(v,4) for v in obj.dimensions], flush=True)
