"""Author part-specific finish controls on the retained UV0; data, not colour art."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=1;s.render.bake.margin=12
s.render.bake.use_selected_to_active=False
r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
values={'M24_bolt':(.31,.55,0),'M24_boltrear':(.34,.55,0),'M24_trigger':(.36,.55,0),'M24_clip':(.38,.55,0),'M24_bullet':(.32,.5,1),'M24_cheekrest':(.42,.58,0),'M24_silencer':(.44,.58,0)}
for group,size,default in [('Body',2048,(.40,.54,0)),('Scope',4096,(.43,.58,0))]:
    obs=[o for o in s.objects if o.type=='MESH' and any(m and m.name=='M24_'+group for m in o.data.materials)]
    image=bpy.data.images.new('T_M24_'+group+'_Regions',width=size,height=size,alpha=False)
    image.colorspace_settings.name='Non-Color';image.generated_color=(*default,1)
    def mat(value):
        m=bpy.data.materials.new('Finish control');m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
        em=n.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*value,1)
        out=n.new('ShaderNodeOutputMaterial');l.new(em.outputs[0],out.inputs['Surface'])
        target=n.new('ShaderNodeTexImage');target.image=image;n.active=target;return m
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.hide_set(False);o.hide_render=False;o.select_set(True);o.data.materials.clear();o.data.materials.append(mat(values.get(o.name,default)))
        if o.name=='M24_base':
            o.data.materials.append(mat((.40,.72,0)))
            for p in o.data.polygons:
                if sum(o.data.vertices[i].co.y for i in p.vertices)/len(p.vertices)<-.326:p.material_index=1
    bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.bake(type='EMIT',use_clear=True)
    image.filepath_raw=str(O/'Textures'/(image.name+'.png'));image.file_format='PNG';image.save()
    print('M24_REGIONS_SAVED',group,flush=True)
(O/'region_recipe.json').write_text(json.dumps({'channels':{'R':'target metallic roughness','G':'target dielectric roughness; > .65 rear recoil pad','B':'preserve source colour (cartridge)'},'object_overrides':values,'base':(.40,.54,0),'scope':(.43,.58,0),'rubber_source_region':'M24_base face centroid Y < -0.326 m'},indent=2),encoding='utf-8')
