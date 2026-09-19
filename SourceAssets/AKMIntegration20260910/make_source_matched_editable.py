import bpy
from pathlib import Path
O=Path(__file__).parent
wood=(O/'Redwood/make_editable_source.py').read_text()
wood=wood.replace('O=Path(__file__).parent',"O=Path(__file__).parent/'Redwood'")
wood=wood.replace("'NativeBaseline/AKM_MannyNative_Editable.blend'","'SourceMatched/AKM_MannyNative_Editable.blend'")
wood=wood[:wood.index('bpy.ops.file.pack_all()')]
exec(compile(wood,__file__,'exec'))
O=Path(__file__).parent
texpath=O.parent/'ChestZiarat20260909/Source/dirty_metal_rmmodbdp_4k__extracted/Textures/T_rmmodbdp_4K_MR.png'
for name in ['M_AKMR_BluedSteel','M_AKMR_BoltSteel','M_AKMR_Parkerized']:
 m=bpy.data.materials[name];m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Metallic'].default_value=.95
 uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=3;l.new(uv.outputs['UV'],scale.inputs[0])
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(texpath),check_existing=True);t.image.colorspace_settings.name='Non-Color';l.new(scale.outputs[0],t.inputs['Vector'])
 ch=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],ch.inputs[0])
 rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.20;rough.inputs[2].default_value=.28;l.new(ch.outputs['Green'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
 mask=n.new('ShaderNodeMath');mask.operation='MULTIPLY_ADD';mask.inputs[1].default_value=-.18;mask.inputs[2].default_value=1;l.new(ch.outputs['Red'],mask.inputs[0])
 color=n.new('ShaderNodeVectorMath');color.operation='SCALE';color.inputs[0].default_value=(.075,.085,.10);l.new(mask.outputs[0],color.inputs[3]);l.new(color.outputs[0],bs.inputs['Base Color'])
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SourceMatched/AKM_Fab_SourceMatched_Editable.blend'))
print('AKM_FAB_EDITABLE_PASS')
