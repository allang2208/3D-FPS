import bpy
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")
print("UV_BEFORE", [(i, l.name, l.active_render) for i, l in enumerate(obj.data.uv_layers)])
keep = obj.data.uv_layers.get("UV_AliceAtlas")
for layer in list(obj.data.uv_layers):
    if layer != keep:
        obj.data.uv_layers.remove(layer)
obj.data.uv_layers.active = keep
keep.active_render = True
print("UV_AFTER", [(i, l.name, l.active_render) for i, l in enumerate(obj.data.uv_layers)])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
print("UV_CLEAN saved")