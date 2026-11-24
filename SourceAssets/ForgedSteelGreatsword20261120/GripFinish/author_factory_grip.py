"""Keep the stock grip's fitted vertices and divide its wrap from the original fittings."""
from pathlib import Path
import bpy
import math
from mathutils import Vector

HERE=Path(__file__).resolve().parent
ART=HERE/'Art/ReferenceLeather'
name='SM_ForgedSteelGreatsword_Grip_FactoryLeather'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(HERE.parent/'Integration/ForgedSteelGreatsword_Modular_Editable.blend')) as (_,lib):
    lib.objects=['SM_ForgedSteelGreatsword_Grip_V1']
obj=lib.objects[0]
bpy.context.scene.collection.objects.link(obj)
obj.name=obj.data.name=name
obj.location=(0,0,0)
wrap=bpy.data.materials.new('M_SharedGrip_Leather')
wrap.use_nodes=True
nodes=wrap.node_tree.nodes; link=wrap.node_tree.links.new
bs=nodes.get('Principled BSDF')
for suffix,pin in [('BaseColor','Base Color'),('Normal','Normal'),('Roughness','Roughness')]:
    sample=nodes.new('ShaderNodeTexImage')
    image=bpy.data.images.load(str(ART/('Leather_'+suffix+'.png')))
    image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
    sample.image=image
    output=sample.outputs['Color']
    if suffix=='Normal':
        bump=nodes.new('ShaderNodeNormalMap'); link(output,bump.inputs['Color']);output=bump.outputs['Normal']
    link(output,bs.inputs[pin])
mesh=obj.data; mesh.materials.append(wrap)
uv=mesh.uv_layers.active.data
for poly in mesh.polygons:
    z=poly.center.z*100
    if not (-16.4<z<-1.3) or -9.75<z<-8.35:continue
    poly.material_index=1
    coords=[mesh.vertices[mesh.loops[k].vertex_index].co for k in poly.loop_indices]
    us=[(math.atan2(v.y,v.x)/math.tau)%1 for v in coords]
    seam=max(us)-min(us)>.5
    for i,k in enumerate(poly.loop_indices):
        u=us[i]+int(seam and us[i]<.5)
        uv[k].uv=Vector((u,coords[i].z/.108))
for img in bpy.data.images:
    if img.source=='FILE' and not img.packed_file and Path(bpy.path.abspath(img.filepath)).is_file():img.pack()
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(ART/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,use_triangles=True,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'FactoryGrip.blend'),compress=True)
