"""Requested offline appearance review, using the actual rebuilt geometry."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018'
bpy.ops.wm.open_mainfile(filepath=str(O/'Authoring/Saiga12K_SurfaceRebuilt.blend'));scene=bpy.context.scene
main=bpy.data.objects['Saiga12K_SurfaceRebuilt'];ext=bpy.data.objects['Saiga12K_Ext12_SurfaceRebuilt'];ext.hide_render=True
if '--saved-ue' in sys.argv:
 d=json.loads((O/'Authoring/saved_ue_gun.json').read_text());materials={m.name.removeprefix('Saiga12K_'):m for m in main.data.materials};names=list(dict.fromkeys(d['parts']));me=bpy.data.meshes.new('Saved UE seated gun');me.from_pydata([(v[0],-v[1],v[2]) for v in d['positions']],[],[t[::-1] for t in d['triangles']]);me.update()
 for name in names:me.materials.append(materials[name])
 for f,k in zip(me.polygons,d['parts']):f.material_index=names.index(k);f.use_smooth=True
 me.normals_split_custom_set([(n[0],-n[1],n[2]) for row in d['normals'] for n in row[::-1]]);uv=me.uv_layers.new(name='UV0')
 for f,row in zip(me.polygons,d['uv']):
  for i,v in zip(f.loop_indices,row[::-1]):uv.data[i].uv=(v[0],1-v[1])
 main.data=me
for ob,key in [(main,'gun'),(ext,'ext12')]:
 normal=O/('Textures/T_Saiga12K_'+key+'_N.png')
 if normal.exists() and '--geometry-only' not in sys.argv:
  im=bpy.data.images.load(str(normal));im.colorspace_settings.name='Non-Color'
  for m in ob.data.materials:
   nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0';tx=nt.nodes.new('ShaderNodeTexImage');tx.image=im;nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(uv.outputs['UV'],tx.inputs['Vector']);nt.links.new(tx.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;n=world.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');bg.inputs[0].default_value=(.075,.075,.075,1);bg.inputs[1].default_value=.5;out=n.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs[0]);scene.world=world
def light(name,p,power,size,size_y,target=(0,-13,0)):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='RECTANGLE';d.size=size;d.size_y=size_y;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('Broad key',(45,-25,60),160000,90,35);light('Side strip',(-35,-15,40),120000,75,12);light('Fill',(45,40,5),65000,55,45);light('Top',(0,-5,80),100000,95,25)
cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.render.resolution_percentage=100
def render(name,target,offset,span,res=(1920,1080)):
 cam.location=Vector(target)+Vector(offset);cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=span;scene.render.resolution_x=res[0];scene.render.resolution_y=res[1];scene.render.filepath=str(O/('Preview/'+name+'.png'));bpy.ops.render.render(write_still=True)
render('SavedUE_Hero' if '--saved-ue' in sys.argv else 'Actual_Hero',(0,-14,-1),(120,24,43),103)
if '--saved-ue' in sys.argv:
 (O/'Reports/saved-render.json').write_text(json.dumps({'geometry':'independent UE saved-package export in native idle frame','source':'Authoring/saved_ue_gun.json','image':'Preview/SavedUE_Hero.png','renderer':'Blender Cycles; UE texture sources and matched scalar finishes; studio lighting','engine_runtime_capture':False},indent=2),encoding='utf-8')
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'Preview/SavedUEReview.blend'),compress=True);sys.exit(0)
render('Actual_Right',(0,-14,-1),(-120,-24,32),103)
render('Actual_Receiver',(0,-4,3),(-100,-26,32),37,(1600,1100))
render('Actual_Top',(0,-14,3),(28,0,110),103)
main.hide_render=True;ext.hide_render=False;ext.hide_set(False)
render('Actual_Ext12',(0,-17,-6),(100,12,18),34,(1100,1400))
(O/'Reports/render.json').write_text(json.dumps({'source':'actual Blender production mesh','baked_normals':(O/'Textures/T_Saiga12K_gun_N.png').exists(),'views':['Actual_Hero','Actual_Right','Actual_Receiver','Actual_Top','Actual_Ext12'],'lighting':'same neutral studio; continuous area emitters; AgX','engine_runtime_capture':False},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Preview/ActualReview.blend'),compress=True)
