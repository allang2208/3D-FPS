"""Targeted V4 candidate-only engine parity. Run only in authorized UE authoring session.
Does not change geometry, textures, production map, formal mesh or shared materials.
"""
import unreal as u,json
from pathlib import Path
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
D='/Game/Props/GodSpaceCoreStarfield20261005/DetailV4/Materials/'
assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert '-CoreDetailV4Authoring' in u.SystemLibrary.get_command_line()
star=u.load_asset(D+'M_CoreStarfield_V4');gold=u.load_asset(D+'M_CoreEngravedGold_V4')
assert star and gold,'Exact V4 candidate materials missing; do not substitute formal/shared materials'
# Preserve emissive HLSL and all texture sampling, depth and rim controls.
star.modify();star.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
errors=L.recompile_material(star);assert not errors,errors
# Keep physical metal; broaden overly narrow daylight highlights locally.
# Replace just the roughness input with a new explicit ORM.G + parameter branch.
orm=u.load_asset('/Game/Props/GodSpaceCoreStarfield20261005/DetailV4/Textures/T_CoreGold_ORM');assert orm
if E.get_metadata_tag(gold,'CoreV4EngineParity')!='unlit-sphere_roughness-bias-018':
 gold.modify()
 def node(cls,**p):
  n=L.create_material_expression(gold,cls,0,0)
  for k,v in p.items():n.set_editor_property(k,v)
  return n
 uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
 t=node(u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 b=node(u.MaterialExpressionScalarParameter,parameter_name='GoldRoughnessBias',default_value=.18)
 add=node(u.MaterialExpressionAdd);clamp=node(u.MaterialExpressionClamp,min_default=.38,max_default=.62)
 for a,out,c,inp in [(uv,'',t,'UVs'),(t,'G',add,'A'),(b,'',add,'B'),(add,'',clamp,'')]:assert L.connect_material_expressions(a,out,c,inp)
 assert L.connect_material_property(clamp,'',u.MaterialProperty.MP_ROUGHNESS)
 E.set_metadata_tag(gold,'CoreV4EngineParity','unlit-sphere_roughness-bias-018')
errors=L.recompile_material(gold);assert not errors,errors
for m in [star,gold]:assert E.save_loaded_asset(m,False)
print(json.dumps({'sphere':star.get_path_name(),'sphere_model':'UNLIT','gold':gold.get_path_name(),'gold_roughness':'clamp(ORM.G + GoldRoughnessBias, .38, .62)','bias_default':.18,'visual_acceptance':False,'runtime_PIE':False}))
