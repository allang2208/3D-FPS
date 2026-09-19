import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'NativeBaseline/AKM_MannyNative_Editable.blend'))
mat=bpy.data.materials.get('M_AKMR_Walnut');assert mat
mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=2;l.new(uv.outputs['UV'],scale.inputs[0])
tex={}
for k in ['Color','NormalGL','Roughness']:
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O/'Wood051'/f'Wood051_2K-JPG_{k}.jpg'))
    if k!='Color':t.image.colorspace_settings.name='Non-Color'
    l.new(scale.outputs['Vector'],t.inputs['Vector']);tex[k]=t
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(1.6,.58,.32,1);l.new(tex['Color'].outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],bs.inputs['Base Color'])
normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.18;l.new(tex['NormalGL'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY_ADD';mul.inputs[1].default_value=.25;mul.inputs[2].default_value=.24;l.new(tex['Roughness'].outputs['Color'],mul.inputs[0]);l.new(mul.outputs[0],bs.inputs['Roughness'])
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_Redwood_Editable.blend'));print('AKM_REDWOOD_SOURCE_PASS')
