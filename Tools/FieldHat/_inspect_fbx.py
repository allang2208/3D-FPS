import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r"D:/FPS3D/FPSGAME/SourceAssets/FieldHat20261019/Exports/FieldHat.fbx")
for obj in bpy.context.scene.objects:
    print("OBJECT", obj.type, obj.name)
    if obj.type == "MESH":
        print("  MATERIALS", [m.name if m else None for m in obj.data.materials])
        print("  GROUPS", [g.name for g in obj.vertex_groups])
    if obj.type == "ARMATURE":
        print("  BONES", [(b.name, b.parent.name if b.parent else None, tuple(round(v,3) for v in b.head_local)) for b in obj.data.bones])
