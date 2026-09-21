import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_Refined_Editable.blend'))
mat=bpy.data.materials['M_A762_Flash_Hider'];n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
regions=n.new('ShaderNodeVertexColor');regions.layer_name='SurfaceRegions';sep=n.new('ShaderNodeSeparateColor');l.new(regions.outputs['Color'],sep.inputs['Color'])
mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.021,.028,.039,1);mix.inputs[2].default_value=(.004,.006,.009,1);l.new(sep.outputs['Red'],mix.inputs[0]);l.new(mix.outputs[0],bs.inputs['Base Color'])
rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=.30;rough.inputs['To Max'].default_value=.79;l.new(sep.outputs['Red'],rough.inputs['Value']);l.new(rough.outputs['Result'],bs.inputs['Roughness'])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_Refined_Editable.blend'))
print('Editable muzzle interior finish saved.')
