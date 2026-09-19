"""Add only the per-rifle receiver cover; the 5080 stock geometry stays unchanged."""
import bpy,math,json
from pathlib import Path
P=Path(__file__).parent;(P/'AKM').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'ReferenceStock5080_Game_Editable.blend'))
stock=bpy.data.objects['SM_SkeletonStock'];stock.hide_set(False);stock.hide_render=False
bpy.ops.mesh.primitive_cube_add(size=1,location=(.16,0,-.25));plate=bpy.context.object;plate.name='AKM_Receiver_Cover';plate.dimensions=(.5,4.1,3.8);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mat=bpy.data.materials.new('M_AKM_StockAdapter');mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.035,.044,.052,1);bs.inputs['Metallic'].default_value=.85;bs.inputs['Roughness'].default_value=.55;plate.data.materials.append(mat)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=1.35,depth=1.5,location=(.16,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;bpy.context.view_layer.objects.active=plate
m=plate.modifiers.new('Tube passage','BOOLEAN');m.object=cut;m.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
m=plate.modifiers.new('Machined edge','BEVEL');m.width=.055;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
for f in plate.data.polygons:f.use_smooth=True
m=plate.modifiers.new('Planar normals','WEIGHTED_NORMAL');bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.select_all(action='DESELECT');plate.select_set(True);stock.select_set(True);bpy.context.view_layer.objects.active=stock;bpy.ops.object.join()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AKM/ReferenceStock5080_AKM_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'AKM/SM_SkeletonStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
stock.data.calc_loop_triangles();print('AKM_ADAPTER_PASS',len(stock.data.loop_triangles))
