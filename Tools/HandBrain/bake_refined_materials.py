import bpy,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/material_v03')
bpy.ops.wm.open_mainfile(filepath=str(R/'HandBrain_Refined.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8
s.render.bake.margin=12;s.render.bake.use_clear=True;s.render.bake.use_selected_to_active=False
rig=bpy.data.objects['SK_HandBrain'];rig.data.pose_position='REST'
report=json.loads((R/'material_report.json').read_text());manifest=[]
for objname in dict.fromkeys(d['object'] for d in report['materials']):
 obj=bpy.data.objects[objname]
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
 for sem in ['BaseColor','Roughness','Normal_DirectX']:
  imgs=[];restore=[]
  for i,m in enumerate(obj.data.materials):
   resolution=4096 if i==0 and objname=='HandBrain_Body' else 2048
   img=bpy.data.images.new(objname+'_'+str(i)+'_'+sem,resolution,resolution,alpha=False)
   img.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color'
   nodes=m.node_tree.nodes;links=m.node_tree.links
   target=nodes.new('ShaderNodeTexImage');target.image=img;nodes.active=target;target.select=True
   out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs['Surface'].links[0].from_socket
   if sem!='Normal_DirectX':
    key='base' if sem=='BaseColor' else 'rough';sock=nodes[m['bake_'+key+'_node']].outputs[m['bake_'+key+'_socket']]
    em=nodes.new('ShaderNodeEmission');links.new(sock,em.inputs['Color']);links.new(em.outputs[0],out.inputs['Surface']);restore.append((m,out,old,em))
   imgs.append((i,img))
  if sem=='Normal_DirectX':
   bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
  else:bpy.ops.object.bake(type='EMIT')
  for m,out,old,em in restore:m.node_tree.links.new(old,out.inputs['Surface']);m.node_tree.nodes.remove(em)
  for i,img in imgs:
   path=R/'textures'/(img.name+'.png');img.filepath_raw=str(path);img.file_format='PNG';img.save()
   manifest.append({'object':objname,'slot':i,'semantic':sem,'path':str(path),'size':list(img.size)})
   print('BAKED',path,flush=True)
rig.data.pose_position='POSE'
(R/'bake_manifest.json').write_text(json.dumps(manifest,indent=2))
print('HANDBRAIN_BAKE_COMPLETE')
