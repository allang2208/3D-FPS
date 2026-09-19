"""Create the selected Meshy stock's game mesh, UV atlas and authored PBR surfaces."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
P=Path(__file__).resolve().parent; T=P/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Imported_Source.blend'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.name='TacticalStock_Selected_High'
# The first 60 mm of source space contains the front sleeve alone, excluding the sling plate.
origin=Vector((-.9519699215888977,.0005147941410541534,.32249777019023895))
scale=.23/(.9512306451797485-origin.x)
high.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(-origin)@high.matrix_world);high.matrix_world=Matrix.Identity(4);high.data.update()
mat=bpy.data.materials.new('SourceHighGeometry');mat.use_nodes=True
high.data.materials.clear();high.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT');high.select_set(True);bpy.context.view_layer.objects.active=high
bpy.ops.object.duplicate();low=bpy.context.object;low.name='TacticalStock_Game_Body';low.data=low.data.copy()
dec=low.modifiers.new('Game silhouette reduction','DECIMATE');dec.ratio=80000/len(low.data.polygons);dec.use_collapse_triangulate=True
print('DECIMATE_START',flush=True);bpy.ops.object.modifier_apply(modifier=dec.name)
tri=low.modifiers.new('Final tangent triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
if low.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
for f in low.data.polygons:f.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70),island_margin=.008,area_weight=.2,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT');low.data.uv_layers[0].name='GeneratedUV0'
low.data.uv_layers.active_index=0;low.data.uv_layers[0].active_render=True
# Five decimated slivers have averaged corner normals parallel to the tangent.
# Split just their shading normals and give them independent bake islands.
low.data.calc_tangents(uvmap='GeneratedUV0')
repair_faces=[f.index for f in low.data.polygons if any(low.data.loops[i].tangent.length<.0001 for i in f.loop_indices)]
uv=low.data.uv_layers[0]
for item in uv.data:item.uv*=.97
for index,fi in enumerate(repair_faces):
 low.data.polygons[fi].use_smooth=False
 x=.975+(index%4)*.005;y=.01+(index//4)*.005
 for li,co in zip(low.data.polygons[fi].loop_indices,[(x,y),(x+.004,y),(x,y+.004)]):uv.data[li].uv=co
low.data.free_tangents();low.data.update();print('REPAIRED_SLIVER_NORMAL_FACES',len(repair_faces),flush=True)
target=bpy.data.images.new('TacticalStock_Normal_Game',width=4096,height=4096,alpha=False);target.colorspace_settings.name='Non-Color'
lowmat=mat.copy();lowmat.name='TacticalStock_BakeTarget';low.data.materials.clear();low.data.materials.append(lowmat)
node=lowmat.node_tree.nodes.new('ShaderNodeTexImage');node.image=target;lowmat.node_tree.nodes.active=node
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.bake.use_selected_to_active=True;scene.render.bake.use_cage=False;scene.render.bake.cage_extrusion=.0007;scene.render.bake.max_ray_distance=.002;scene.render.bake.margin=16;scene.render.bake.normal_space='TANGENT'
bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalStock_Bake_Editable.blend'))
print('NORMAL_BAKE_START',len(low.data.polygons),flush=True);bpy.ops.object.bake(type='NORMAL')
target.filepath_raw=str(T/'Normal_Game.png');target.file_format='PNG';target.save()
high.hide_render=True;high.hide_set(True);high.select_set(False);scene.render.bake.use_selected_to_active=False
# Distinguish the rear pad, adjustable cheek housing, and exposed metal mechanism.
labels=[]
for f in low.data.polygons:
 x,y,z=f.center
 rubber=x>.219
 cheek=.071<x<.219 and -.022<z<.005 and ((x-.097)**2+(z+.012)**2)>.018**2
 labels.append(2 if rubber else 1 if cheek else 0)
low.data.materials.clear();mats=[]
colors=[(.026,.029,.033,1),(.025,.028,.032,1),(.012,.014,.016,1)]
rough=[.44,.59,.86];metal=[1.,0.,0.]
for i,name in enumerate(['Metal','Polymer','Rubber']):
 m=bpy.data.materials.new('TacticalStock_'+name);m.use_nodes=True;mats.append(m);low.data.materials.append(m)
 n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');emit=n.new('ShaderNodeEmission');l.new(emit.outputs[0],out.inputs['Surface'])
 tex=n.new('ShaderNodeTexImage');n.active=tex
for f,label in zip(low.data.polygons,labels):f.material_index=label
for key in ['BaseColor','Roughness','Metallic']:
 im=bpy.data.images.new('TacticalStock_'+key,width=4096,height=4096,alpha=False);im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
 for i,m in enumerate(mats):
  n=m.node_tree.nodes;l=m.node_tree.links;tex=next(t for t in n if t.type=='TEX_IMAGE');tex.image=im;n.active=tex
  emit=next(t for t in n if t.type=='EMISSION')
  value=colors[i] if key=='BaseColor' else (rough[i],)*3+(1,) if key=='Roughness' else (metal[i],)*3+(1,)
  emit.inputs['Color'].default_value=value
 print('AUTHOR_ATLAS',key,flush=True);bpy.ops.object.bake(type='EMIT');im.filepath_raw=str(T/(key+'.png'));im.file_format='PNG';im.save()
for m in mats:
 n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs['Surface']);uv=n.new('ShaderNodeUVMap');uv.uv_map='GeneratedUV0'
 for key in ['BaseColor','Roughness','Metallic','Normal_Game']:
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images['TacticalStock_'+key] if key!='Normal_Game' else target;l.new(uv.outputs[0],t.inputs['Vector'])
  if key=='Normal_Game':
   nm=n.new('ShaderNodeNormalMap');nm.uv_map='GeneratedUV0';l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
  else:l.new(t.outputs['Color'],bs.inputs['Base Color' if key=='BaseColor' else key])
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalStock_Game_Body.blend'))
(P/'body_authoring.json').write_text(json.dumps({'source_triangles':len(high.data.polygons),'game_triangles':len(low.data.polygons),'mount_origin_source':list(origin),'length_m':.23,'front_sleeve_radii_m':[.00994,.01231],'orientation':'front -X; buttpad +X; up +Z','source_uv_or_materials':False,'uv0':'authored smart projection atlas','pbr':'authored dark polymer and rubber; metal is replaced by per-rifle receiver coating on UV1','normal':'selected high to low geometry, OpenGL tangent normal','material_face_counts':{name:labels.count(i) for i,name in enumerate(['metal','polymer','rubber'])},'gameplay_tested':False},indent=2))
print('TACTICAL_GAME_BODY_COMPLETE',flush=True)
