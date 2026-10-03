"""Resume production icon creation from the completed editable model."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
root=Matrix(json.loads((O/'authoring.json').read_text())['root'])
body=bpy.data.objects['Drum50_AuthoredBody'];neck=bpy.data.objects['Retained_G18_Feed_Neck'];scene=bpy.context.scene
mat=neck.data.materials[0];n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
for ch,input_name in [('Base_color','Base Color'),('Roughness','Roughness')]:
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O.parent/'G18Integration20260929/Textures'/('T_G18_'+ch+'.png')),check_existing=True)
    t.image.colorspace_settings.name='sRGB' if ch=='Base_color' else 'Non-Color'
    if ch=='Base_color':
        scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=.10;l.new(t.outputs[0],scale.inputs[0])
        add=n.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.004,.005,.006);l.new(scale.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs[input_name])
    else:
        lower=n.new('ShaderNodeMath');lower.operation='MAXIMUM';lower.inputs[1].default_value=.34;l.new(t.outputs[0],lower.inputs[0]);l.new(lower.outputs[0],bs.inputs[input_name])
bs.inputs['Metallic'].default_value=.40
normal_tex=n.new('ShaderNodeTexImage');normal_tex.image=bpy.data.images.load(str(O.parent/'G18Integration20260929/Textures/T_G18_Normal_DirectX.png'),check_existing=True);normal_tex.image.colorspace_settings.name='Non-Color'
sep=n.new('ShaderNodeSeparateColor');l.new(normal_tex.outputs[0],sep.inputs[0]);inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;l.new(sep.outputs['Green'],inv.inputs[1])
comb=n.new('ShaderNodeCombineColor');l.new(sep.outputs['Red'],comb.inputs['Red']);l.new(inv.outputs[0],comb.inputs['Green']);l.new(sep.outputs['Blue'],comb.inputs['Blue']);norm=n.new('ShaderNodeNormalMap');l.new(comb.outputs[0],norm.inputs['Color']);l.new(norm.outputs[0],bs.inputs['Normal'])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
for ob in (body,neck):ob.data.transform(root.inverted())
target=Vector((0,.045,-.125))
bpy.ops.object.camera_add(location=target+Vector((-.30,.63,.11)));cam=bpy.context.object;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.35;scene.camera=cam
for loc,power,size in [((-.30,.4,.25),5,.32),((.28,.15,-.1),1.5,.22),((-.12,-.35,-.1),4,.20)]:
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
if not scene.world:scene.world=bpy.data.worlds.new('Drum studio')
scene.world.use_nodes=True;wn=scene.world.node_tree.nodes;wn.clear();background=wn.new('ShaderNodeBackground');background.inputs['Color'].default_value=(.06,.06,.06,1);background.inputs['Strength'].default_value=.4;worldout=wn.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(background.outputs[0],worldout.inputs[0])
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.engine='CYCLES';scene.cycles.samples=64
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(O/'Icons/drum50_source.png');bpy.ops.render.render(write_still=True)
print('G18_DRUM50_V2_ICON_SOURCE_SAVED',flush=True)
