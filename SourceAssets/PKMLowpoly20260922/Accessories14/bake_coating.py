"""Bake the current PKM/QBZ metal recipe onto a private 5 cm coating tile."""
import bpy,ast,json
from pathlib import Path
O=Path(__file__).parent;S=O.parents[1];T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
tree=ast.parse((S/'QBZ191Hero20260913/build.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='material')
env={'bpy':bpy};exec(compile(ast.Module(body=[fn],type_ignores=[]),'PKM_QBZ_coating_recipe','exec'),env)
mat=env['material']('AUTH_PKM14_Coating',(.025,.029,.033),.72,.30)
bpy.ops.mesh.primitive_plane_add(size=.05);ob=bpy.context.object;ob.name='PKM14_CoatingTile';ob.data.materials.append(mat)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=0;s.render.bake.use_clear=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
if any(d.use for d in prefs.devices):s.cycles.device='GPU'
n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
# Match the current installed Unified receiver's final roughness conversion.
raw=bs.inputs['Roughness'].links[0].from_socket
mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.62;l.new(raw,mul.inputs[0])
add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=.42*.38;l.new(mul.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs['Roughness']);l.new(add.outputs[0],n[mat['bake_orm_node']].inputs[1])
emit=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage');n.active=target;paths={}
for channel,socket in [('BaseColor',bs.inputs['Base Color'].links[0].from_socket),('ORM',n[mat['bake_orm_node']].outputs[0]),('Normal',None)]:
 im=bpy.data.images.new('T_PKM14_Coating_'+channel,width=1024,height=1024,alpha=False);im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';target.image=im
 if socket:l.new(socket,emit.inputs[0]);l.new(emit.outputs[0],out.inputs[0])
 else:l.new(bs.outputs[0],out.inputs[0])
 bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
 im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();paths[channel]=im.filepath_raw
 print('PKM14_COATING_BAKED',channel,flush=True)
l.new(bs.outputs[0],out.inputs[0]);target.image=None
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Coating_Editable.blend'))
(O/'coating.json').write_text(json.dumps({'reference':'/Game/Weapons/PKMLowpoly20260922/Bipod07/Materials/M_PKM_QBZ_Body','recipe':'QBZ191Hero20260913/build.py material(), matching Bipod07 receiver recipe','linear_base_color':[.025,.029,.033],'metallic':.72,'roughness_recipe':'.62 * (.30 + noise * .035) + .42 * .38','physical_tile_m':.05,'uv_channel':2,'textures':paths,'structural_normals':'Preserve donor UV0 normals; coating normal used only on new metal interfaces','AO':'Neutral coating R=1; preserve donor AO'},indent=2))
print('PKM14_COATING_COMPLETE',flush=True)
