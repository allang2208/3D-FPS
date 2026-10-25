"""Save the shared seal material with a separate runtime gold color parameter."""
import ast
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[3]
D='/Game/Weapons/CommonHammerSeats20261024/AncientSealV1'
TAG='AncientSealOwner';OWNER='AncientSealBuildV1_20261024'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'game_tested':False,'mesh_reused':'SM_AncientSeal_TargetMark'}
helpers=ROOT/'SourceAssets/RuneboundWarhammer20261022/RuneAndBellRefinement20261024/install_assets.py'
tree=ast.parse(helpers.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<material_helpers>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
m=material('M_AncientSeal_TargetMark')
m.set_editor_property('used_with_nanite',False)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
alpha=node(m,u.MaterialExpressionScalarParameter,parameter_name='MarkOpacity',default_value=0.)
color=node(m,u.MaterialExpressionVectorParameter,parameter_name='MarkColor',default_value=u.LinearColor(2.28,.768,.192,1.))
surface(m,{'basecolor':vector(m,(0,0,0)),'roughness':constant(m,1.),'metallic':constant(m,0.),'specular':constant(m,0.),'emissivecolor':color,'opacity':alpha})
stats=L.get_statistics(m)
receipt['gpu_compilation']={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions}
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('Material GPU compilation did not finish')
save(m)
receipt['complete']=True;record()
print('ANCIENT_SEAL_OVERHEAD_GOLD_MATERIAL_SAVED')
