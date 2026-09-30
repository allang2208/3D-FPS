import bpy
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
exec((O/'inspect_shapes.py').read_text().split("shot('closed_shape'")[0])
rec=bpy.data.objects['Receiver']
bpy.ops.object.select_all(action='DESELECT');rec.select_set(True);bpy.context.view_layer.objects.active=rec;bpy.ops.mesh.customdata_custom_splitnormals_clear()
for p in rec.data.polygons:p.use_smooth=False
shot('receiver_flat',(.135,.10,.185),(0,-.155,.064),.235)
with bpy.data.libraries.load(str(O.parent/'Surface32/LMG201_S32_Editable.blend'),link=False) as (src,dst):dst.objects=['Receiver']
original=dst.objects[0];scene.collection.objects.link(original)
xf=root.inverted()@original.matrix_world;original.data.transform(xf);original.parent=None;original.matrix_world=Matrix.Identity(4);original.modifiers.clear();original.hide_render=False;original.hide_set(False)
rec.hide_render=True
shot('receiver_original',(.135,.10,.185),(0,-.155,.064),.235)
