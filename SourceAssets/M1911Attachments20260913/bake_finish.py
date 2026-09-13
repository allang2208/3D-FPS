"""Bake the accepted M1911 slide coating as a physical 10 cm material tile."""
import bpy,ast
from pathlib import Path
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
source=(O.parent/'M1911Hero20260913/build.py').read_text(encoding='utf-8')
shader_ast=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='shader')
exec(compile(ast.Module(body=[shader_ast],type_ignores=[]),'<M1911 accepted coating>','exec'))
m=shader('AttachmentBluedSlide',(.022,.028,.036),.26,.88)
bpy.ops.mesh.primitive_plane_add(size=.1);ob=bpy.context.object;ob.data.materials.append(m)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=0
n=m.node_tree.nodes;l=m.node_tree.links;out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
emit=n.new('ShaderNodeEmission');l.new(emit.outputs[0],out.inputs['Surface'])
for kind in ['BaseColor','ORM']:
    image=bpy.data.images.new('T_M1911_Attachment_'+kind,width=1024,height=1024,alpha=False)
    image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    target=n.new('ShaderNodeTexImage');target.image=image;n.active=target
    origin=n[m['base_node']].outputs[m['base_socket']] if kind=='BaseColor' else n[m['orm_node']].outputs[0]
    l.new(origin,emit.inputs['Color']);bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Coating_Editable.blend'))
print('M1911_ATTACHMENT_COATING_BAKED',flush=True)
