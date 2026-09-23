"""Diagnose why the kit blend renders empty: collection visibility, view layer, scene."""
from pathlib import Path
import bpy
from mathutils import Vector

KIT = 'D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonWorkbenchKit.blend'
bpy.ops.wm.open_mainfile(filepath=KIT)
print('SCENES', [s.name for s in bpy.data.scenes], 'ACTIVE', bpy.context.scene.name)
for sc in bpy.data.scenes:
    print('SCENE', sc.name, 'objects', len(sc.objects), 'frame', sc.frame_current)
print('COLLECTIONS')
def walk(coll, depth=0):
    print('  ' * depth, coll.name, 'hide_viewport', coll.hide_viewport, 'hide_render', coll.hide_render,
          'objects', len(coll.objects), 'children', len(coll.children))
    for ch in coll.children: walk(ch, depth + 1)
for lc in bpy.context.scene.layer_collection.children:
    print('LAYER', lc.name, 'exclude', lc.exclude)
walk(bpy.context.scene.collection)
for name in ('SM_WBK_Bench_BenchTop', 'SM_WBK_Sculpt_BenchFrame'):
    ob = bpy.data.objects.get(name)
    if ob:
        print(name, 'hide_render', ob.hide_render, 'hide_viewport', ob.hide_viewport,
              'visible_get', ob.visible_get(), 'loc', tuple(round(v, 2) for v in ob.location),
              'collections', [c.name for c in ob.users_collection])
