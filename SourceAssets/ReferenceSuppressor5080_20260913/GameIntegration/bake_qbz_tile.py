"""Bake the existing QBZ receiver coating into a reusable physical tile."""
import bpy
from pathlib import Path

O=Path(__file__).resolve().parent
source=Path('D:/FPS3D/FPSGAME/SourceAssets/QBZ191MetalCoat20260913/QBZ191_ReceiverCoating_Editable.blend')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source),link=False) as (data,target):
    target.materials=[name for name in data.materials if name=='AUTH_QBZ191_ReceiverCoating']
m=target.materials[0].copy()
bpy.ops.mesh.primitive_plane_add(size=.1)
ob=bpy.context.object;ob.data.materials.append(m)
n=m.node_tree.nodes;l=m.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
emit=n.new('ShaderNodeEmission');l.new(emit.outputs[0],out.inputs['Surface'])
combine=n.new('ShaderNodeCombineColor');combine.inputs[0].default_value=1
for prop,index in [('Roughness',1),('Metallic',2)]:
    socket=bs.inputs[prop]
    if socket.is_linked:l.new(socket.links[0].from_socket,combine.inputs[index])
    else:combine.inputs[index].default_value=socket.default_value
base=bs.inputs['Base Color']
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=0
for kind in ['BaseColor','ORM']:
    image=bpy.data.images.new('T_TacticalSuppressor_QBZ191_'+kind,width=1024,height=1024,alpha=False)
    image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    tex=n.new('ShaderNodeTexImage');tex.image=image;n.active=tex
    if kind=='BaseColor':
        if base.is_linked:l.new(base.links[0].from_socket,emit.inputs['Color'])
        else:emit.inputs['Color'].default_value=base.default_value
    else:l.new(combine.outputs[0],emit.inputs['Color'])
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(O/'Textures'/(image.name+'.png'));image.file_format='PNG';image.save()
    print('QBZ_TACTICAL_COATING_BAKED',kind,flush=True)
