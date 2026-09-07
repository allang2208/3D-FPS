import bpy,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent;kind=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=json.loads((P/'sources.json').read_text(encoding='utf-8'))[kind])
scene=bpy.context.scene
body=next(o for o in scene.objects if o.type=='MESH');arm=next(o for o in scene.objects if o.type=='ARMATURE')
arm.data.pose_position='REST'
mat=body.data.materials[0];nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
original=bs.inputs['Base Color'].links[0].from_socket
# Native Blender HSV node: retain hue identity, strengthen muted colors.
hsv=nt.nodes.new('ShaderNodeHueSaturation');hsv.label='Richer existing palette'
hsv.inputs['Saturation'].default_value=1.65
hsv.inputs['Value'].default_value=1.08
nt.links.new(original,hsv.inputs['Color'])
color=hsv.outputs['Color']
output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
emit=nt.nodes.new('ShaderNodeEmission');nt.links.new(emit.outputs[0],output.inputs[0])
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=8
images={}
for channel,socket in [('albedo',color)]:
 if isinstance(socket,(float,int)):emit.inputs['Color'].default_value=(socket,socket,socket,1)
 else:nt.links.new(socket,emit.inputs['Color'])
 im=bpy.data.images.new(kind+'_'+channel,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if channel=='albedo' else 'Non-Color'
 tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im
 for n in nt.nodes:n.select=False
 tex.select=True;nt.nodes.active=tex
 bpy.ops.object.bake(type='EMIT')
 im.filepath_raw=str(P/(kind+'-'+channel+'.png'));im.file_format='PNG';im.save();im.pack();images[channel]=tex
 for link in list(emit.inputs['Color'].links):nt.links.remove(link)
nt.links.new(bs.outputs[0],output.inputs[0])
nt.links.new(images['albedo'].outputs['Color'],bs.inputs['Base Color'])

for link in list(bs.inputs['Metallic'].links):nt.links.remove(link)
bs.inputs['Metallic'].default_value=0
arm.data.pose_position='POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(P/(kind+'-unified.blend')))
print('STYLE_BAKE_COMPLETE',kind)
