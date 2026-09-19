"""Create a game derivative of the selected Meshy stock and bake its surface normals."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Imported_Source.blend'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.name='Meshy_Selected_High'
front=-.9517890214920044;rear=.9512050151824951
# The upper front tube is widest around z=.488; the lower latch is excluded.
origin=Vector((front,.0004,.488));scale=.2/(rear-front)
frame=Matrix.Scale(scale,4)@Matrix.Translation(-origin)@high.matrix_world
high.data.transform(frame);high.matrix_world=Matrix.Identity(4);high.data.update()
high.data.uv_layers[0].name='GeneratedUV0'
mat=bpy.data.materials.new('Meshy_Source_Surface');mat.use_nodes=True
n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
uv=n.new('ShaderNodeUVMap');uv.uv_map='GeneratedUV0'
for key in ['BaseColor','Metallic','Roughness','Normal']:
    im=bpy.data.images.load(str(P/'Textures'/(key+'.png')),check_existing=True);im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
    t=n.new('ShaderNodeTexImage');t.image=im;l.new(uv.outputs['UV'],t.inputs['Vector'])
    if key=='Normal':
        nm=n.new('ShaderNodeNormalMap');nm.uv_map='GeneratedUV0';l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
    else:l.new(t.outputs['Color'],bs.inputs['Base Color' if key=='BaseColor' else key])
high.data.materials.clear();high.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT');high.select_set(True);bpy.context.view_layer.objects.active=high
bpy.ops.object.duplicate();low=bpy.context.object;low.name='CoreStock_Game_Body';low.data=low.data.copy()
mod=low.modifiers.new('Game silhouette reduction','DECIMATE');mod.ratio=80000/sum(len(p.vertices)-2 for p in low.data.polygons);mod.use_collapse_triangulate=True;mod.delimit={'UV','SEAM','SHARP'}
bpy.ops.object.modifier_apply(modifier=mod.name)
# Finalize game tangent geometry before baking high geometry and source normal detail.
tri=low.modifiers.new('Final triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
low.data.uv_layers.active_index=0;low.data.uv_layers[0].active_render=True
target=bpy.data.images.new('CoreStock_Game_Normal',width=4096,height=4096,alpha=False,float_buffer=False);target.colorspace_settings.name='Non-Color'
lowmat=mat.copy();lowmat.name='CoreStock_BakeTarget';low.data.materials.clear();low.data.materials.append(lowmat)
node=lowmat.node_tree.nodes.new('ShaderNodeTexImage');node.image=target;lowmat.node_tree.nodes.active=node;node.select=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.bake.use_selected_to_active=True;scene.render.bake.use_cage=False;scene.render.bake.cage_extrusion=.001;scene.render.bake.max_ray_distance=.003;scene.render.bake.margin=16;scene.render.bake.normal_space='TANGENT'
bpy.ops.object.select_all(action='DESELECT');high.hide_set(False);high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
bpy.ops.wm.save_as_mainfile(filepath=str(P/'CoreStock_Bake_Editable.blend'))
print('BAKE_GAME_NORMAL_START',len(low.data.polygons),flush=True)
bpy.ops.object.bake(type='NORMAL')
target.filepath_raw=str(P/'Textures'/'Normal_Game.png');target.file_format='PNG';target.save()
# Set the produced normal on the game source; remove the bake target feedback node.
lowmat.node_tree.nodes.remove(node)
for t in lowmat.node_tree.nodes:
    if t.type=='TEX_IMAGE' and t.image and t.image.name.startswith('Normal'):t.image=target
high.hide_render=True;high.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CoreStock_Low_Editable.blend'))
(P/'low_authoring.json').write_text(json.dumps({'source_triangles':sum(len(p.vertices)-2 for p in high.data.polygons),'game_body_triangles':sum(len(p.vertices)-2 for p in low.data.polygons),'mount_origin_source':list(origin),'body_length_m':.2,'source_uv_preserved':0,'normal_bake':'Textures/Normal_Game.png','bake_samples':16,'cage_extrusion_m':.001,'max_ray_distance_m':.003,'runtime_tested':False,'preview_rendered':False},indent=2))
print('GAME_BODY_AUTHORED',flush=True)
