import bpy,json
import numpy as np
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');o=r/'sculpt_v06';(o/'textures').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(o/'HandBrain_Sculpt_Source.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU'
rig=bpy.data.objects['SK_HandBrain'];rig.data.pose_position='REST'
low=bpy.data.objects['HandBrain_Body'];high=bpy.data.objects['HandBrain_Sculpt_High'];high.hide_set(False);high.hide_render=False
bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.0035;s.render.bake.max_ray_distance=.007;s.render.bake.margin=12;s.render.bake.use_clear=True
manifest=json.loads((r/'realism_v05/bake_manifest.json').read_text())
# Bake a surface mask so projection changes never overwrite the face or unrelated skin.
coords=np.empty(len(high.data.vertices)*3,dtype=np.float32);high.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
normals=np.empty_like(coords);high.data.vertices.foreach_get('normal',normals.ravel());mask=np.zeros(len(coords),np.float32)
for f in json.loads((o/'projected_features.json').read_text())['features']:
 c=np.array(f['center']);a=np.array(f['axis']);b=np.array(f['side']);n=np.array(f['normal']);L=max(f['length'],.009);W=max(f['width'],.009)
 ids=np.where(np.all(np.abs(coords-c)<max(L,W)*3+.025,axis=1))[0];d=coords[ids]-c
 weight=np.exp(-.5*((d@a/L)**2+(d@b/W)**2+(d@n/.014)**2))*np.clip((normals[ids]@n-.2)/.6,0,1)
 mask[ids]=np.maximum(mask[ids],weight)
attr=high.data.attributes.get('SculptArea') or high.data.attributes.new('SculptArea','FLOAT','POINT');attr.data.foreach_set('value',np.clip(mask*2,0,1))
for sem in ['BaseColor','Mask','Normal_DirectX']:
 target=low if sem=='Normal_DirectX' else high
 bpy.ops.object.select_all(action='DESELECT');target.select_set(True);bpy.context.view_layer.objects.active=target
 s.render.bake.use_selected_to_active=sem=='Normal_DirectX'
 if sem=='Normal_DirectX':high.select_set(True)
 images=[];restore=[]
 for i,m in enumerate(target.data.materials):
  img=bpy.data.images.new('Sculpt_Body_'+str(i)+'_'+sem,4096 if i==0 else 2048,4096 if i==0 else 2048,alpha=False)
  img.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color'
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=img;m.node_tree.nodes.active=n;images.append((i,img))
 for m in high.data.materials:
  if sem=='Normal_DirectX':continue
  nodes=m.node_tree.nodes;links=m.node_tree.links;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs[0].links[0].from_socket
  if sem=='Mask':
   attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='SculptArea';sock=attr.outputs['Fac']
  else:sock=nodes[m['bake_base_node']].outputs[m['bake_base_socket']]
  em=nodes.new('ShaderNodeEmission');links.new(sock,em.inputs[0]);links.new(em.outputs[0],out.inputs[0]);restore.append((m,out,old,em))
 if sem=='Normal_DirectX':bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
 else:bpy.ops.object.bake(type='EMIT')
 for m,out,old,em in restore:m.node_tree.links.new(old,out.inputs[0]);m.node_tree.nodes.remove(em)
 for i,img in images:
  path=o/'textures'/(img.name+'.png');img.filepath_raw=str(path);img.file_format='PNG';img.save()
  if i==0 and sem!='Mask':
   row=next(v for v in manifest if v['object']=='HandBrain_Body' and v['slot']==i and v['semantic']==sem);row.update(path=str(path),size=list(img.size))
  print('SCULPT_BAKED',path,flush=True)
high.hide_render=True;high.hide_set(True);rig.data.pose_position='POSE'
(o/'bake_manifest.json').write_text(json.dumps(manifest,indent=2))
(o/'material_report.json').write_text((r/'realism_v05/material_report.json').read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(o/'HandBrain_Refined.blend'))
print('HANDBRAIN_SCULPT_BAKED')
