"""Same old installed M16 mesh, fixed camera/light, isolate the normal bake."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;P=O.parents[1];V=O/'Preview';V.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
source=P/'SourceAssets/M16StockDonor20261015/Final/SM_M16_tactical_telescopic.fbx'
bpy.ops.import_scene.fbx(filepath=str(source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
frame=Matrix.Translation(Vector((-.000038,.041045,.0917)))@Matrix.Rotation(math.pi/2,4,'Z')
for o in objects:o.matrix_world=frame.inverted()@o.matrix_world
report={'source':str(source),'meshes':[],'renders':[]}
for o in objects:
 report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.polygons),'uvs':[l.name for l in o.data.uv_layers],'custom_normals':o.data.has_custom_normals,'materials':[m.name if m else None for m in o.data.materials]})
points=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(lo+hi)/2;report['bounds']=[list(lo),list(hi)]
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
world=bpy.data.worlds.new('AB_Studio');world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.22,.24,.27,1);bg.inputs[1].default_value=.6;scene.world=world
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
for name,xyz,power,size in [('Key',(.04,-.30,.30),8,.35),('Fill',(.32,-.3,.04),3,.22),('Rim',(.25,.16,.22),7,.25)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=xyz;aim(o)
camera=bpy.data.objects.new('AB_Camera',bpy.data.cameras.new('AB_Camera'));scene.collection.objects.link(camera);scene.camera=camera
camera.location=center+Vector((.085,-.65,.05));camera.data.type='ORTHO';camera.data.ortho_scale=.28;camera.data.clip_start=.001;aim(camera)
original_normals={o.name:[tuple(n.vector) for n in o.data.corner_normals] for o in objects}
def material(name,normal_path,metal=.8,rough=.32):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs['Surface'])
 bs.inputs['Base Color'].default_value=(.16,.17,.18,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 if normal_path:
  im=bpy.data.images.load(str(normal_path),check_existing=True);im.colorspace_settings.name='Non-Color'
  tex=n.new('ShaderNodeTexImage');tex.image=im
  uv=n.new('ShaderNodeUVMap');uv.uv_map=objects[0].data.uv_layers[0].name;l.new(uv.outputs[0],tex.inputs['Vector'])
  nm=n.new('ShaderNodeNormalMap');nm.uv_map=uv.uv_map;l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
 return m
variants=[('A_constant_no_texture',None,.8,.32),
 ('B_R2_structural_normal',P/'SourceAssets/M16AttachmentSurface20261014/Detail/T_TelescopicStructuralDetail_R2.png',.8,.32),
 ('C_original_bake_normal',P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/Textures/Normal_Game.png',.8,.32),
 ('D_white_diffuse_no_texture',None,0,.8)]
for name,path,metal,rough in variants:
 mat=material(name,path,metal,rough)
 for o in objects:
  for i in range(len(o.data.materials)):o.data.materials[i]=mat
 scene.render.filepath=str(V/(name+'.png'));bpy.ops.render.render(write_still=True)
 report['renders'].append({'name':name,'normal':str(path) if path else None,'metallic':metal,'roughness':rough});print('AB_SAVED',name,flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Diagnostic_AB_Editable.blend'))
(O/'diagnosis_render.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
