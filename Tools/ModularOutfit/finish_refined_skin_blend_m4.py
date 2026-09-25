"""Save the V3 editable model with its baked skin and licensed detail source."""
import runpy,json,bpy
from pathlib import Path
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=Path(globals().get('AUTHOR_ROOT',PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3'))
runpy.run_path(str(PROJECT/'Tools/ModularOutfit/finish_original_shape_blend.py'),init_globals={'AUTHOR_ROOT':str(ROOT),'KEEP_MATERIAL_PARTITION':True})
obj=bpy.data.objects['M4_OriginalShape_BareHands'];skin=obj.data.materials[-1]
nodes=skin.node_tree.nodes;links=skin.node_tree.links;bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
normal=next(n for n in nodes if n.type=='NORMAL_MAP');cfg=json.loads((ROOT/'micro_surface.json').read_text())
tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'T_M4OriginalShape_SkinMicro.png'))
tex.image.colorspace_settings.name='Non-Color';tex.image.pack()
uv=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=cfg['tile_repeat']
links.new(uv.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],tex.inputs['Vector'])
separate=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],separate.inputs['Color'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=cfg['height_range_cm']*.01
links.new(separate.outputs['Blue'],bump.inputs['Height']);links.new(normal.outputs['Normal'],bump.inputs['Normal']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
bsdf.inputs['Subsurface Weight'].default_value=.08
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M4_OriginalShape_BareHands_Editable.blend'))
print('REFINED_SKIN_EDITABLE_SAVED')
