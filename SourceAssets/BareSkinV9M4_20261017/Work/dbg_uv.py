import bpy, bmesh, numpy as np
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017')
d = np.load(R / 'Work/mesh.npz'); T = d['T']
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('M4Skin')
me.from_pydata([tuple(p) for p in d['X']], [], [tuple(int(v) for v in t) for t in T]); me.update()
obj = bpy.data.objects.new('M4Skin', me); bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj; obj.select_set(True)
new = me.uv_layers.new(name='new')
uv = d['UV'].reshape(-1, 2).copy(); uv[:, 1] = 1 - uv[:, 1]; new.data.foreach_set('uv', uv.ravel())
def ext(tag):
    a = np.zeros(len(me.loops)*2); me.uv_layers['new'].data.foreach_get('uv', a); a=a.reshape(-1,2)
    print('DBG', tag, a.min(0), a.max(0), np.isnan(a).sum())
ext('init')
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
print('DBG ctx', bpy.context.mode, bpy.context.tool_settings.use_uv_select_sync)
r = bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.001); print('DBG unwrap', r)
bpy.ops.object.mode_set(mode='OBJECT'); ext('unwrap'); bpy.ops.object.mode_set(mode='EDIT')
r = bpy.ops.uv.select_all(action='SELECT'); print('DBG selall', r)
r = bpy.ops.uv.average_islands_scale(); print('DBG avg', r)
bpy.ops.object.mode_set(mode='OBJECT'); ext('avg'); bpy.ops.object.mode_set(mode='EDIT')
r = bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.004); print('DBG pack', r)
bpy.ops.object.mode_set(mode='OBJECT'); ext('pack')
