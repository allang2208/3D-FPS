"""Refine the current SVD magazine and bake its own UV atlas; no preview render."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector

O=Path(__file__).parent;S=O.parent;T=O/'Textures';T.mkdir(exist_ok=True)
D=O/'Exports';D.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMagazineFit20260923/SVD_base_Editable.blend'))
scene=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST'
bpy.context.view_layer.update()
mag=bpy.data.objects['SM_SVD_Magazine'];inside=bpy.data.objects['SM_SVD_MagazineInterior']
X=(r.matrix_world@r.data.bones['WPN_SOCKET_Magazine'].matrix_local).inverted()@mag.matrix_world
source_faces=len(mag.data.polygons)

def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

# Weld positional seam duplicates on the magazine only, restore source split
# normals, then cut tiny bevels inside the existing stamped-shell silhouette.
donor=mag.copy();donor.data=mag.data.copy();donor.name='MAG_NORMAL_DONOR';bpy.context.collection.objects.link(donor)
for mod in list(donor.modifiers):donor.modifiers.remove(mod)
for mod in list(mag.modifiers):mag.modifiers.remove(mod)
active(mag)
bm=bmesh.new();bm.from_mesh(mag.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bm.to_mesh(mag.data);bm.free();mag.data.update()
transfer=mag.modifiers.new('RetainFactoryCornerNormals','DATA_TRANSFER');transfer.object=donor
transfer.use_loop_data=True;transfer.data_types_loops={'CUSTOM_NORMAL'};transfer.loop_mapping='POLYINTERP_NEAREST'
bpy.ops.object.modifier_apply(modifier=transfer.name)
bev=mag.modifiers.new('StampedSteelEdgeRadius','BEVEL');bev.width=.00018;bev.segments=3
bev.limit_method='ANGLE';bev.angle_limit=math.radians(32);bev.use_clamp_overlap=True;bev.harden_normals=True
bpy.ops.object.modifier_apply(modifier=bev.name)
bpy.data.objects.remove(donor,do_unlink=True)

# A shallow rolled floorplate follows the actual angled lower case plane.
# Its body lies in the original shell; the tiny lip is below the grasp region.
points=[X@v.co for v in mag.data.vertices]
slope=-.21871;intercept=-.028055
forward=Vector((0,1,slope)).normalized();normal=Vector((0,-slope,1)).normalized()
y0=-.0249;y1=.0609;center=Vector((-.000046,(y0+y1)/2,slope*(y0+y1)/2+intercept))
half_width=.01053;half_length=(y1-y0)*math.sqrt(1+slope*slope)/2
radius=.00125;loop=[]
for cx,cy,base in [(half_width-radius,half_length-radius,0),(-half_width+radius,half_length-radius,90),
                   (-half_width+radius,-half_length+radius,180),(half_width-radius,-half_length+radius,270)]:
 for step in range(9):
  angle=math.radians(base+step*90/8)
  loop.append((cx+radius*math.cos(angle),cy+radius*math.sin(angle)))
verts=[]
for inset,height in [(.00025,.0008),(0,.00055),(0,-.00005),(.00023,-.00022)]:
 for x,y in loop:
  p=center+Vector((x*(1-inset/half_width),0,0))+forward*y*(1-inset/half_length)+normal*height
  verts.append(X.inverted()@p)
n=len(loop);faces=[]
for j in range(3):
 for i in range(n):k=(i+1)%n;faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
faces += [tuple(reversed(range(n))),tuple(range(3*n,4*n))]
faces=[tuple(reversed(face)) for face in faces]
me=bpy.data.meshes.new('SVD_FloorplateRolledEdge');me.from_pydata(verts,[],faces);me.update()
floor=bpy.data.objects.new('SM_SVD_MagazineFloorplate',me);bpy.context.collection.objects.link(floor)
floor.matrix_world=mag.matrix_world.copy();floor.data.materials.append(inside.data.materials[0])
floor.vertex_groups.new(name='WPN_SOCKET_Magazine').add(list(range(len(me.vertices))),1,'REPLACE')
uv=me.uv_layers.new(name='UVMap')
for f in me.polygons:
 for li in f.loop_indices:
  p=X@me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p.x/.04+.5,p.y/.12+.3)
# Keep each object's valid first UV as UV0 when joining, as in PKM Hands29.
for ob in [mag,inside,floor]:
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 ob.data.uv_layers[0].name='UVMap';ob.data.uv_layers.active_index=0
active(mag);inside.select_set(True);floor.select_set(True);bpy.ops.object.join()
mag=bpy.context.object;mag.name='SM_SVD_Magazine'
# All magazine geometry is rigidly attached to its existing mechanical bone.
for group in list(mag.vertex_groups):mag.vertex_groups.remove(group)
mag.vertex_groups.new(name='WPN_SOCKET_Magazine').add(list(range(len(mag.data.vertices))),1,'REPLACE')
high=mag.copy();high.data=mag.data.copy();high.name='BAKE_SVD_MagazineSource'
bpy.context.collection.objects.link(high);high.parent=None;high.matrix_world=mag.matrix_world.copy()
for i,m in enumerate(high.data.materials):high.data.materials[i]=m.copy()
# A dedicated 4K UV atlas raises usable magazine texel density. The complete
# source structural normal is baked from the donor's original corrected UV0.
active(mag);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.012)
bpy.ops.object.mode_set(mode='OBJECT')
target_material=bpy.data.materials.new('SVD_Magazine_BakeTarget');target_material.use_nodes=True
original_slots=[m for m in mag.data.materials]
for i in range(len(mag.data.materials)):mag.data.materials[i]=target_material
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.render.bake.use_selected_to_active=True;scene.render.bake.use_clear=True
scene.render.bake.cage_extrusion=.00025;scene.render.bake.max_ray_distance=.0015;scene.render.bake.margin=16
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
for ob in scene.objects:
 if ob.type=='MESH':ob.hide_render=ob not in [mag,high]
maps={}
saved_links={}
for m in high.data.materials:
 nodes=m.node_tree.nodes;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
 saved_links[m.name]=out.inputs['Surface'].links[0].from_socket
for kind in ['BaseColor','ORM','Normal']:
 image=bpy.data.images.new('T_SVD_Magazine_'+kind,width=4096,height=4096,alpha=False)
 image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
 target=target_material.node_tree.nodes.get('BAKE_TARGET') or target_material.node_tree.nodes.new('ShaderNodeTexImage')
 target.name='BAKE_TARGET';target.image=image;target_material.node_tree.nodes.active=target
 for m in high.data.materials:
  nodes=m.node_tree.nodes;links=m.node_tree.links;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
  bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
  if kind=='Normal':links.new(saved_links[m.name],out.inputs['Surface']);continue
  emit=nodes.get('BAKE_EMISSION') or nodes.new('ShaderNodeEmission');emit.name='BAKE_EMISSION'
  if kind=='BaseColor':
   inp=bs.inputs['Base Color'];value=inp.links[0].from_socket if inp.is_linked else None
   if value:links.new(value,emit.inputs['Color'])
   else:emit.inputs['Color'].default_value=inp.default_value
  else:
   texture=next((n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'ORM' in n.image.name),None)
   if texture:links.new(texture.outputs['Color'],emit.inputs['Color'])
   else:
    for link in list(emit.inputs['Color'].links):links.remove(link)
    emit.inputs['Color'].default_value=(.94,.60,.84,1)
  links.new(emit.outputs[0],out.inputs['Surface'])
 active(mag);high.select_set(True)
 bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
 image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save();maps[kind]=image
 print('SVD_DETAIL_BAKED',kind,flush=True)
for i,m in enumerate(original_slots):
 # Keep stable slot names; both sections now sample the dedicated atlas.
 mag.data.materials[i]=m;nodes=m.node_tree.nodes;links=m.node_tree.links;nodes.clear()
 bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs[0])
 for kind,image in maps.items():
  tex=nodes.new('ShaderNodeTexImage');tex.image=image
  if kind=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
  elif kind=='ORM':
   sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs[0],sep.inputs[0]);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
   matte=nodes.new('ShaderNodeMath');matte.operation='MAXIMUM';matte.inputs[1].default_value=.61
   links.new(sep.outputs['Green'],matte.inputs[0]);links.new(matte.outputs[0],bs.inputs['Roughness'])
  else:
   normalmap=nodes.new('ShaderNodeNormalMap');normalmap.uv_map='UVMap';links.new(tex.outputs[0],normalmap.inputs['Color']);links.new(normalmap.outputs[0],bs.inputs['Normal'])
high.hide_render=True;high.hide_set(True)
mag.modifiers.new('SharedManny','ARMATURE').object=r
active(mag);tri=mag.modifiers.new('FinalTriangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
objects=[o for o in scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]+[r]
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(D/'SK_SVD_Modular.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';scene.frame_set(0)
for ob in objects:
 if ob.type=='MESH':ob.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_MatteDetail_Editable.blend'))
(O/'model_authoring.json').write_text(json.dumps({'source':'SVDMagazineFit20260923/SVD_base_Editable.blend',
 'bevel_mm':.18,'bevel_segments':3,'floorplate_lip_below_original_mm':.22,
 'source_shell_faces':source_faces,'final_magazine_faces':len(mag.data.polygons),'uv':'dedicated packed UV0 4096 squared',
 'normals':'Complete original structural normal rebaked with refined geometry; OpenGL tangent output',
 'slots':[m.name for m in mag.data.materials],'textures':{k:v.filepath_raw for k,v in maps.items()},
 'bone':'WPN_SOCKET_Magazine','animations_changed':False,'rendered_or_game_tested':False},indent=2))
print('SVD_DETAIL_MODEL_AUTHORED',len(mag.data.polygons),flush=True)
