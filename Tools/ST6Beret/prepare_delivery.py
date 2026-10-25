"""Prepare canonical static wear geometry and production inventory art."""
import bpy,json,sys,importlib.util
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6Beret20261023/SurfaceV2';KEY='ue_st6_tactical_helmet'
bpy.ops.wm.open_mainfile(filepath=str(R/'Exports/ST6_Beret_Burgundy_Editable.blend'))
deps=bpy.context.evaluated_depsgraph_get();parts=[]
col=bpy.data.collections.new('Delivery_Combined');bpy.context.scene.collection.children.link(col)
for original in list(bpy.data.collections['01_ST6_Beret_Editable'].objects):
    if original.type not in ('MESH','FONT'):continue
    me=bpy.data.meshes.new_from_object(original.evaluated_get(deps),depsgraph=deps,preserve_all_data_layers=True)
    source_materials=[s.material for s in original.material_slots]
    me.materials.clear()
    for material in source_materials:
        if material is None:raise RuntimeError('Unassigned source material: '+original.name)
        me.materials.append(material)
    if not me.uv_layers:
        uv=me.uv_layers.new(name='PhysicalScaleUV')
        for f in me.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
            for li in f.loop_indices:
                p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04,p[axes[1]]/.04)
    me.uv_layers.active.name='PhysicalScaleUV'
    ob=bpy.data.objects.new(original.name+'_Delivery',me);col.objects.link(ob);ob.matrix_world=original.matrix_world.copy();parts.append(ob)
for ob in list(bpy.context.scene.objects):
    if ob not in parts:ob.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='ST6_Beret_Delivery';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active
d=dict(profile='ST6Beret',positions=[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in me.vertices],triangles=[],normals=[],uv=[],triangle_materials=[],material_slots=[m.name for m in me.materials])
for tri in me.loop_triangles:
    d['triangles'].append(list(tri.vertices));d['triangle_materials'].append(tri.material_index)
    d['normals'].append([[me.corner_normals[li].vector.x,-me.corner_normals[li].vector.y,me.corner_normals[li].vector.z] for li in tri.loops]);d['uv'].append([[uv.data[li].uv.x,1-uv.data[li].uv.y] for li in tri.loops])
(R/'Authored/hat.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
families={'ST6_Wine_WoolFelt':'ST6_BurgundyFelt','ST6_Black_Leather':'ST6_BlackLeather','ST6_Burgundy_SatinLining':'ST6_Lining','ST6_DarkSilver':'ST6_DarkSilver'}
mats=[]
for mat in me.materials:
    bs=mat.node_tree.nodes.get('Principled BSDF');mats.append(dict(name=mat.name,family=families.get(mat.name),color=list(bs.inputs['Base Color'].default_value)[:3],roughness=bs.inputs['Roughness'].default_value,metallic=bs.inputs['Metallic'].default_value,cloth=mat.name=='ST6_Wine_WoolFelt'))
(R/'materials.json').write_text(json.dumps(mats,indent=2),encoding='utf-8')
# The established inventory pipeline generates the actual 320px item icon,
# calibrated surface color and matching camera-aligned display geometry.
spec=importlib.util.spec_from_file_location('st6_inventory_art',str(P/'Tools/FieldHat/render_icon.py'));icons=importlib.util.module_from_spec(spec)
source=(P/'Tools/FieldHat/render_icon.py').read_text(encoding='utf-8')
source=source.replace('world.use_nodes = True','world.use_nodes = True\n    world.node_tree.nodes.clear()\n    background = world.node_tree.nodes.new("ShaderNodeBackground")\n    background.name = "Background"\n    output = world.node_tree.nodes.new("ShaderNodeOutputWorld")\n    world.node_tree.links.new(background.outputs[0], output.inputs[0])')
exec(compile(source,str(P/'Tools/FieldHat/render_icon.py'),'exec'),icons.__dict__)
icons.OUT=R;icons.FAMILIES={KEY:'ST6Beret20261023/SurfaceV2'}
item=dict(grid_w=2,grid_h=2,ue_icon='Icons/ST6Beret20261023/'+KEY+'.png')
icons.render_current(KEY,ob,item=item,camera_offset=(-.85,3.,1.25))
receipt=json.loads((R/'authored.json').read_text(encoding='utf-8'));receipt.update(stage='refined_model_and_inventory_art',original_texture_maps=16,delivery_triangles=len(d['triangles']),materials=len(mats),inventory_icon_rendered=True,preview_rendered=False)
(R/'authored.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('ST6_BERET_DELIVERY_PREPARED',len(d['triangles']),len(mats),flush=True)
