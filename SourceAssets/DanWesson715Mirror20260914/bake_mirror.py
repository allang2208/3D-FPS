"""Reuse the established UV0 bake/rig pipeline with the new mirror shader.

All changes occur in this revision. The source retains the latest accepted
reload actions and the four fitted attachment alternatives. No preview/test.
"""
import ast
import sys
from pathlib import Path
O=Path(__file__).parent
sys.path.insert(0,str(O))
source=(O.parent/'DanWesson715MetalFinish20260914/bake_finish.py').read_text(encoding='utf-8')
tree=ast.parse(source)
lines=source.splitlines(keepends=True)
remove=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='author_material' or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FINISH' for t in node.targets)]
for node in sorted(remove,key=lambda n:n.lineno,reverse=True):
    lines[node.lineno-1:node.end_lineno]=['from mirror_material import FINISH, author_material\n'] if isinstance(node,ast.Assign) else []
program=''.join(lines)
program=program.replace('DanWesson715LeftRecovery20260914/DanWesson715_LeftRecovery_Editable.blend','DanWesson715Attachments20260914/DanWesson715_Attachments_Editable.blend')
program=program.replace("info = prior[group]","info = dict(prior[group], size=4096)")
program=program.replace("materials[group, 'SourceEngraving' in old.name]","materials[group, 'SourceEngraving' in old.name or '_Engraving' in old.name]")
program=program.replace('T_DW715_Finish_','T_DW715_Mirror_').replace('M_DW715_Finish_','M_DW715_Mirror_')
program=program.replace('DanWesson715_MetalFinish_Editable.blend','DanWesson715_Mirror_Editable.blend')
program=program.replace('DW715_METAL_FINISH_SOURCE_COMPLETE','DW715_MIRROR_SOURCE_COMPLETE').replace('DW715_FINISH_BAKED','DW715_MIRROR_BAKED')
exec(compile(program,str(O/'bake_mirror.py'),'exec'),globals())

# Make the corresponding physical coating tile for this gun's attachments.
# Retain the complete source; use a temporary plane after it has been saved.
import bpy,json
from mirror_material import author_material
bpy.ops.wm.read_factory_settings(use_empty=True)
m=author_material('Steel');bpy.ops.mesh.primitive_plane_add(size=.1);ob=bpy.context.object;ob.data.materials.append(m)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=8;s.render.bake.use_selected_to_active=False
n=m.node_tree.nodes;l=m.node_tree.links;out=next(x for x in n if x.type=='OUTPUT_MATERIAL');em=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage');n.active=target
maps={}
for kind in ['BaseColor','ORM']:
    image=bpy.data.images.new('T_DW715_Mirror_Attachment_'+kind,width=1024,height=1024,alpha=False);image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';target.image=image
    value=n[m['base_node']].outputs[m['base_socket']] if kind=='BaseColor' else n[m['orm_node']].outputs[0]
    l.new(value,em.inputs[0]);l.new(em.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(O/'Textures'/(image.name+'.png'));image.file_format='PNG';image.save();maps[kind]=image.filepath_raw
l.new(next(x for x in n if x.type=='BSDF_PRINCIPLED').outputs[0],out.inputs['Surface'])
(O/'attachment-finish.json').write_text(json.dumps({'textures':maps,'physical_tile_m':.1,'finish':'Mirror Steel','roughness':.06},indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DW715_MirrorCoating_Editable.blend'))
print('DW715_MIRROR_COATING_COMPLETE',flush=True)
