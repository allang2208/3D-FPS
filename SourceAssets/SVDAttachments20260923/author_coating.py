"""Bake SVD receiver coating at its recorded physical grain scale (no normal rebake)."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
parameters=json.loads((O.parent/'SVDSurface20260923/authoring.json').read_text())['finish_parameters']['Receiver']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.mesh.primitive_plane_add(size=.05);ob=bpy.context.object;ob.name='SVD_5cm_CoatingTile'
m=bpy.data.materials.new('SVD_ReceiverCoating_Author');m.use_nodes=True;ob.data.materials.append(m)
n=m.node_tree.nodes;l=m.node_tree.links;n.clear();uv=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value=1150;noise.inputs['Detail'].default_value=2;l.new(uv.outputs['Object'],noise.inputs['Vector'])
def scalar(op,a,b):
 q=n.new('ShaderNodeMath');q.operation=op
 for v,p in zip([a,b],q.inputs):
  if hasattr(v,'node'):l.new(v,p)
  else:p.default_value=v
 return q.outputs[0]
base=n.new('ShaderNodeRGB');base.outputs[0].default_value=(*parameters[0],1)
rough=scalar('ADD',parameters[2],scalar('MULTIPLY',scalar('SUBTRACT',noise.outputs['Fac'],.5),.026))
orm=n.new('ShaderNodeCombineColor');orm.inputs[0].default_value=1;l.new(rough,orm.inputs[1]);orm.inputs[2].default_value=parameters[1]
out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');l.new(em.outputs[0],out.inputs[0])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=0
for role,value in [('BaseColor',base.outputs[0]),('ORM',orm.outputs[0])]:
 im=bpy.data.images.new('T_SVD_AttachmentCoat_'+role,4096,4096,alpha=False)
 im.colorspace_settings.name='sRGB' if role=='BaseColor' else 'Non-Color';im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG'
 target=n.new('ShaderNodeTexImage');target.image=im;n.active=target;l.new(value,em.inputs[0]);bpy.ops.object.bake(type='EMIT');im.save()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_Coating_Editable.blend'))
(O/'coating.json').write_text(json.dumps({'reference':'SVDSurface20260923 Receiver','parameters':parameters,'tile_m':.05,'roughness_grain_scale_per_m':1150,'original_normal':'retained UV0 / unchanged strength','textures':['T_SVD_AttachmentCoat_BaseColor','T_SVD_AttachmentCoat_ORM']},indent=2))
print('SVD_ATTACH_COATING_BAKED',flush=True)
