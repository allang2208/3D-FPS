"""Create the skill's post-tonemap blur, excluding foreground stencil 231."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
folder='/Game/Skills/Whirlwind20260920';name='M_WhirlwindFocus'
path=folder+'/'+name
if L.does_asset_exist(path):raise RuntimeError('Focus material exists; preserve edits: '+path)
L.make_directory(folder)
mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
mat.set_editor_property('blendable_priority',20)
color=M.create_material_expression(mat,u.MaterialExpressionSceneTexture,-650,-160)
color.set_editor_property('scene_texture_id',u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
color.set_editor_property('filtered',True)
stencil=M.create_material_expression(mat,u.MaterialExpressionSceneTexture,-650,80)
stencil.set_editor_property('scene_texture_id',u.SceneTextureId.PPI_CUSTOM_STENCIL)
strength=M.create_material_expression(mat,u.MaterialExpressionScalarParameter,-650,300)
strength.set_editor_property('parameter_name','Strength');strength.set_editor_property('default_value',0.0)
custom=M.create_material_expression(mat,u.MaterialExpressionCustom,-240,0)
custom.set_editor_property('code',(P/'focus_blur.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property('description','Background yaw blur; stencil 231 keeps held weapon and arms crisp')
inputs=[]
for name in ('ColorInput','StencilInput','Strength'):
    item=u.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
custom.set_editor_property('inputs',inputs)
for source,pin in ((color,'ColorInput'),(stencil,'StencilInput'),(strength,'Strength')):
    if not M.connect_material_expressions(source,'',custom,pin):raise RuntimeError('Material connection failed: '+pin)
if not M.connect_material_property(custom,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Material output connection failed')
errors=M.recompile_material(mat)
if errors:raise RuntimeError('\n'.join(errors))
# UE's Python API exposes the blocking FinishCompilation through GetStatistics.
# Use it only to finish the asset build; no performance report or render is run.
M.get_statistics(mat)
if not L.save_loaded_asset(mat,False):raise RuntimeError('Focus material save failed')
(P/'focus_material_receipt.json').write_text(json.dumps({'asset':mat.get_path_name(),'saved':True,'stencil':231,'pass':'SceneColorAfterTonemapping'},indent=2),encoding='utf-8')
u.log('WHIRLWIND_FOCUS_SAVED '+mat.get_path_name())
