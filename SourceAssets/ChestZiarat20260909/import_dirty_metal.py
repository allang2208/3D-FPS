import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
dest='/Game/ColdSteelUI/Warehouse20260909/DirtyMetal'
lib=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
task=u.AssetImportTask()
for k,v in {'filename':str(root/'Source/dirty_metal_rmmodbdp_4k__extracted/Textures/T_rmmodbdp_4K_MR.png'),'destination_path':dest,'destination_name':'T_DirtyMetal_MR_4K','automated':True,'save':False}.items():task.set_editor_property(k,v)
assets.import_asset_tasks([task])
tex=u.EditorAssetLibrary.load_asset(dest+'/T_DirtyMetal_MR_4K')
assert isinstance(tex,u.Texture2D)
tex.set_editor_property('srgb',False)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
assert u.EditorAssetLibrary.save_loaded_asset(tex,only_if_is_dirty=False)
assert not u.EditorAssetLibrary.does_asset_exist(dest+'/M_Chest_DirtyMetal')
mat=assets.create_asset('M_Chest_DirtyMetal',dest,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('two_sided',True)
lib.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def expr(cls,x,y,**props):
 n=lib.create_material_expression(mat,cls,x,y)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def connect(a,output,b,pin):assert lib.connect_material_expressions(a,output,b,pin)
uv=expr(u.MaterialExpressionTextureCoordinate,-1100,0,u_tiling=3.6,v_tiling=3.6)
sample=expr(u.MaterialExpressionTextureSampleParameter2D,-850,0,parameter_name='DirtyMetal_MaskR_RoughnessG',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
connect(uv,'',sample,'')
tint=expr(u.MaterialExpressionVectorParameter,-800,400,parameter_name='MetalTint',default_value=u.LinearColor(.64,.36,.075,1))
dark=expr(u.MaterialExpressionMultiply,-580,420,const_b=.32);connect(tint,'',dark,'A')
mask=expr(u.MaterialExpressionMultiply,-570,120,const_b=.8);connect(sample,'R',mask,'A')
color=expr(u.MaterialExpressionLinearInterpolate,-300,350);connect(tint,'',color,'A');connect(dark,'',color,'B');connect(mask,'',color,'Alpha')
metal=expr(u.MaterialExpressionLinearInterpolate,-300,650,const_a=.82,const_b=.25);connect(mask,'',metal,'Alpha')
assert lib.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
assert lib.connect_material_property(sample,'G',u.MaterialProperty.MP_ROUGHNESS)
assert lib.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
lib.recompile_material(mat)
assert mat.get_editor_property('used_with_skeletal_mesh')
assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
mi=assets.create_asset('MI_Chest_DirtyMetal_Brass',dest,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(mi,mat)
overrides=mi.get_editor_property('base_property_overrides')
overrides.set_editor_property('override_two_sided',True);overrides.set_editor_property('two_sided',True)
mi.set_editor_property('base_property_overrides',overrides)
lib.update_material_instance(mi)
assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
report={'material':mi.get_path_name(),'parent':mat.get_path_name(),'texture':tex.get_path_name(),'uv_tiling':3.6,'two_sided':True,'skeletal_mesh':True,'channels':{'R':'dirt mask, controls tint and dielectric contamination','G':'roughness','B':'constant white; not a metallic map'},'source_category':'imperfection','base_tint':[.64,.36,.075],'metallic_clean':.82,'metallic_dirty':.25}
(root/'dirty_metal_report.json').write_text(json.dumps(report,indent=2))
u.log('CHEST_DIRTY_METAL_IMPORT_PASS '+mi.get_path_name())
