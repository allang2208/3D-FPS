import json
from pathlib import Path
import unreal as u

root=Path(__file__).parent
src=root/'Source/ziarat_white_marble_tgzk_extracted'
dest='/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble'
assets=u.AssetToolsHelpers.get_asset_tools()
lib=u.MaterialEditingLibrary
textures={}
for role in ['BaseColor','Normal','Roughness','Specular','Cavity']:
 name='T_Ziarat_'+role+'_4K'
 path=dest+'/Textures/'+name
 if not u.EditorAssetLibrary.does_asset_exist(path):
  task=u.AssetImportTask()
  for key,value in {'filename':str(src/('Ziarat_White_Marble_tgzkdehv_4K_'+role+'.jpg')),'destination_path':dest+'/Textures','destination_name':name,'automated':True,'save':False,'replace_existing':False}.items():task.set_editor_property(key,value)
  assets.import_asset_tasks([task])
 tex=u.EditorAssetLibrary.load_asset(path)
 assert isinstance(tex,u.Texture2D),path
 tex.set_editor_property('srgb',role in ['BaseColor','Specular'])
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else u.TextureCompressionSettings.TC_DEFAULT)
 # Raw Megascans texture-set normals retained; no glTF convention conversion.
 if role=='Normal':tex.set_editor_property('flip_green_channel',False)
 assert u.EditorAssetLibrary.save_loaded_asset(tex,only_if_is_dirty=False)
 textures[role]=tex

mp=dest+'/M_Chest_Ziarat'
assert not u.EditorAssetLibrary.does_asset_exist(mp),'Candidate already exists; inspect before rebuilding'
mat=assets.create_asset('M_Chest_Ziarat',dest,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('two_sided',True)
lib.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def expr(cls,x,y,**props):
 n=lib.create_material_expression(mat,cls,x,y)
 for key,value in props.items():n.set_editor_property(key,value)
 return n
uv=expr(u.MaterialExpressionTextureCoordinate,-1000,0,u_tiling=1.8,v_tiling=1.8)
for i,(role,tex) in enumerate(textures.items()):
 sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if role in ['BaseColor','Specular'] else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 node=expr(u.MaterialExpressionTextureSampleParameter2D,-600,i*230,parameter_name=role,texture=tex,sampler_type=sampler)
 assert lib.connect_material_expressions(uv,'',node,'')
 prop={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Normal':u.MaterialProperty.MP_NORMAL,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Specular':u.MaterialProperty.MP_SPECULAR,'Cavity':u.MaterialProperty.MP_AMBIENT_OCCLUSION}[role]
 if role=='Specular':
  # Texture encodes dielectric F0 in sRGB; UE Specular 0..1 maps to F0 0..0.08.
  convert=expr(u.MaterialExpressionMultiply,-280,i*230,const_b=12.5)
  assert lib.connect_material_expressions(node,'R',convert,'A')
  assert lib.connect_material_property(convert,'',prop)
 else:assert lib.connect_material_property(node,'RGB' if role in ['BaseColor','Normal'] else 'R',prop)
lib.recompile_material(mat)
assert mat.get_editor_property('used_with_skeletal_mesh')
assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
mi=assets.create_asset('MI_Chest_Ziarat_4K',dest,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(mi,mat)
overrides=mi.get_editor_property('base_property_overrides')
overrides.set_editor_property('override_two_sided',True);overrides.set_editor_property('two_sided',True)
mi.set_editor_property('base_property_overrides',overrides)
lib.update_material_instance(mi)
assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
report={'material':mi.get_path_name(),'parent':mat.get_path_name(),'uv_tiling':1.8,'two_sided':True,'skeletal_mesh':True,'textures':{k:{'path':t.get_path_name(),'srgb':t.get_editor_property('srgb'),'compression':str(t.get_editor_property('compression_settings'))} for k,t in textures.items()}}
(root/'material_report.json').write_text(json.dumps(report,indent=2))
u.log('CHEST_ZIARAT_IMPORT_PASS '+mi.get_path_name())
