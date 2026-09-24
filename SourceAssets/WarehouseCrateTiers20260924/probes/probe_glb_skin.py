import bpy
bpy.ops.import_scene.gltf(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\ChestRitual20260909\warehouse_chest_ritual_v8.glb')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print('ARM', arm.name, 'bones', [b.name for b in arm.data.bones], flush=True)
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.type == 'MESH':
        print('OBJ', o.name, 'vgroups', [(g.name, g.index) for g in o.vertex_groups],
              'polys', len(o.data.polygons), 'parent', o.parent.name if o.parent else None,
              'mods', [m.type for m in o.modifiers], flush=True)
for a in bpy.data.actions:
    print('ACT', a.name, 'slots', [s.name for s in a.slots], 'range', list(a.frame_range[:]), flush=True)
