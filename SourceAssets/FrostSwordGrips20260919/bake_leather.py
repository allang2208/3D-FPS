"""Author a reusable 2K leather PBR tile in Blender, not an acceptance render."""
import bpy
from pathlib import Path
P=Path(__file__).parent/'Textures';P.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
bpy.context.preferences.filepaths.save_version=0
bpy.ops.mesh.primitive_plane_add(size=.1)
obj=bpy.context.object;m=bpy.data.materials.new('M_Grip_Leather_Bake');m.use_nodes=True;obj.data.materials.append(m)
n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
uv=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=175;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.72
l.new(uv.outputs['UV'],noise.inputs['Vector'])
vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=92;l.new(uv.outputs['UV'],vor.inputs['Vector'])
blend=n.new('ShaderNodeMath');blend.operation='MULTIPLY';l.new(vor.outputs['Distance'],blend.inputs[0]);l.new(noise.outputs['Fac'],blend.inputs[1])
bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00022;bump.inputs['Strength'].default_value=.52;l.new(blend.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.023,.036,.052,1);ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(.066,.085,.105,1);l.new(noise.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=.53;rough.inputs['To Max'].default_value=.72;l.new(noise.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs[0],bs.inputs['Roughness'])
em=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage')
for key,socket,kind in [('base_color',ramp.outputs['Color'],'EMIT'),('roughness',rough.outputs[0],'EMIT'),('normal',None,'NORMAL')]:
    im=bpy.data.images.new('T_GripLeather_'+key,2048,2048,alpha=False)
    if key!='base_color':im.colorspace_settings.name='Non-Color'
    target.image=im;n.active=target
    if kind=='EMIT':l.new(socket,em.inputs['Color']);l.new(em.outputs[0],out.inputs['Surface'])
    else:l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bpy.ops.object.bake(type=kind,margin=4,use_clear=True)
    im.filepath_raw=str(P/(key+'.png'));im.file_format='PNG';im.save()
l.new(bs.outputs['BSDF'],out.inputs['Surface'])
bpy.ops.wm.save_as_mainfile(filepath=str(P/'LeatherMaterial_Editable.blend'))
print('GRIP_LEATHER_BAKED',flush=True)
