import bpy,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/surface_v07');(r/'textures').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(r/'HandBrain_Sculpt_Source.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU';rig=bpy.data.objects['SK_HandBrain'];rig.data.pose_position='REST'
low=bpy.data.objects['HandBrain_Body'];high=bpy.data.objects['HandBrain_Sculpt_High'];high.hide_set(False);high.hide_render=False
s.render.bake.cage_extrusion=.0035;s.render.bake.max_ray_distance=.007;s.render.bake.margin=12
for semantic in ['Mask','Normal_DirectX']:
 target=high if semantic=='Mask' else low
 bpy.ops.object.select_all(action='DESELECT');target.select_set(True);bpy.context.view_layer.objects.active=target
 s.render.bake.use_selected_to_active=semantic!='Mask'
 if semantic!='Mask':high.select_set(True)
 images=[];restore=[]
 for i,m in enumerate(target.data.materials):
  img=bpy.data.images.new('Surface_'+str(i)+'_'+semantic,4096 if i==0 else 2048,4096 if i==0 else 2048,alpha=False);img.colorspace_settings.name='Non-Color'
  node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=img;m.node_tree.nodes.active=node;images.append((i,img))
 if semantic=='Mask':
  for m in high.data.materials:
   nodes=m.node_tree.nodes;links=m.node_tree.links;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs[0].links[0].from_socket
   a=nodes.new('ShaderNodeAttribute');a.attribute_name='SurfaceRegion';em=nodes.new('ShaderNodeEmission');links.new(a.outputs['Fac'],em.inputs[0]);links.new(em.outputs[0],out.inputs[0]);restore.append((m,out,old,em))
  bpy.ops.object.bake(type='EMIT')
 else:bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
 for m,out,old,em in restore:m.node_tree.links.new(old,out.inputs[0]);m.node_tree.nodes.remove(em)
 for i,img in images:
  img.filepath_raw=str(r/'textures'/(img.name+'.png'));img.file_format='PNG';img.save()
 print('SURFACE_BAKED',semantic,flush=True)
high.hide_render=True;high.hide_set(True);rig.data.pose_position='POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(r/'HandBrain_Refined.blend'))
print('SURFACE_BAKE_COMPLETE')
