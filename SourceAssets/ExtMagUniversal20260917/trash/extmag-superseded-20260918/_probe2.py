import bpy, os
RIFLE = r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913\AKM\SK_AKM_MannyNative.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=RIFLE)
for ob in list(bpy.context.scene.objects):
    if ob.type != "MESH":
        continue
    print("PROBE2 mesh", ob.name, len(ob.data.vertices), len(ob.data.polygons),
          [m.name if m else None for m in ob.data.materials], flush=True)
print("PROBE2_DONE", flush=True)
