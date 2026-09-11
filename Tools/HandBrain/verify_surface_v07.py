import bpy,json,sys,numpy as np
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/surface_v07')
bpy.ops.wm.open_mainfile(filepath=str(R/'HandBrain_Refined.blend'))
rows=json.loads((R/'bake_manifest.json').read_text());stats=[]
for objname in dict.fromkeys(d['object'] for d in rows):
 obj=bpy.data.objects[objname]
 for i,old in enumerate(obj.data.materials):
  if False: # V05 lining now has valid UVs
   # No usable UV area on this original local interior; constant tissue shading.
   m=bpy.data.materials.new('Mucosa_no_uv');m.use_nodes=True;obj.data.materials[i]=m
   p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.065,.007,.011,1);p.inputs['Roughness'].default_value=.28
   stats.append({'object':objname,'slot':i,'mode':'constant_mucosa_no_uv','empty_bake_used':False})
   continue
  m=bpy.data.materials.new('Baked_'+objname+'_'+str(i));m.use_nodes=True;obj.data.materials[i]=m
  p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.32
  for sem in ['BaseColor','Roughness','Normal_DirectX']:
   row=next(r for r in rows if r['object']==objname and r['slot']==i and r['semantic']==sem)
   image=bpy.data.images.load(row['path'],check_existing=False);image.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color'
   data=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(data);rgb=data.reshape(-1,4)[:,:3]
   assert np.isfinite(rgb).all() and rgb.max()>.01,row['path']
   stats.append({'path':row['path'],'minimum':float(rgb.min()),'maximum':float(rgb.max()),'stddev':float(rgb.std())})
   n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=image
   if sem=='Normal_DirectX':
    sep=m.node_tree.nodes.new('ShaderNodeSeparateColor');m.node_tree.links.new(n.outputs['Color'],sep.inputs[0]);combine=m.node_tree.nodes.new('ShaderNodeCombineColor');inv=m.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
    m.node_tree.links.new(sep.outputs[1],inv.inputs[1]);m.node_tree.links.new(sep.outputs[0],combine.inputs[0]);m.node_tree.links.new(inv.outputs[0],combine.inputs[1]);m.node_tree.links.new(sep.outputs[2],combine.inputs[2])
    norm=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(combine.outputs[0],norm.inputs['Color']);m.node_tree.links.new(norm.outputs[0],p.inputs['Normal'])
   else:m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color' if sem=='BaseColor' else 'Roughness'])
s=bpy.context.scene;rig=bpy.data.objects['SK_HandBrain'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];s.frame_set(1)
sys.path.insert(0,str(R.parent/'hunyuan_v01'));import studio
studio.aim(s.camera,(5,-3.8,2.7),(.1,0,1.1));s.camera.data.ortho_scale=2.65
s.render.filepath=str(R/'Baked_check.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'HandBrain_Refined_Baked.blend'))
(R/'bake_validation.json').write_text(json.dumps({'maps':stats,'complete':True},indent=2))
print('HANDBRAIN_BAKED_RENDER_COMPLETE')
