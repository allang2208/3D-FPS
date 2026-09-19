import bpy
from pathlib import Path
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(p/'PrismScope2X_Editable.blend'))
o=bpy.data.objects['SM_PrismScope2X_Body'];print('CUSTOM_NORMALS',o.data.has_custom_normals,'smooth',sum(f.use_smooth for f in o.data.polygons),len(o.data.polygons))
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception as e:print(e);o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
m=o.data.materials[0];bs=m.node_tree.nodes.get('Principled BSDF')
for key in ['Normal','Base Color','Metallic','Roughness']:
 for l in list(bs.inputs[key].links):m.node_tree.links.remove(l)
bs.inputs['Base Color'].default_value=(.12,.13,.14,1);bs.inputs['Metallic'].default_value=.0;bs.inputs['Roughness'].default_value=.65
bpy.context.scene.render.filepath=str(p/'diagnostic_normals.png');bpy.ops.render.render(write_still=True)
