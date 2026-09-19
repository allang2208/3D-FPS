import unreal, json, hashlib
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/AKMIntegration/Materials'
lib=unreal.MaterialEditingLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
textures={}
for kind,srgb,compression in [('Color',True,unreal.TextureCompressionSettings.TC_DEFAULT),('NormalDX',False,unreal.TextureCompressionSettings.TC_NORMALMAP),('Roughness',False,unreal.TextureCompressionSettings.TC_GRAYSCALE)]:
    task=unreal.AssetImportTask()
    task.filename=str(O/'Redwood'/'Wood051'/f'Wood051_2K-JPG_{kind}.jpg')
    task.destination_path=P+'/Textures';task.destination_name='T_AKM_Wood051_'+kind
    task.automated=True;task.replace_existing=True;task.save=True
    assets.import_asset_tasks([task])
    tex=unreal.load_asset(task.imported_object_paths[0]);tex.set_editor_property('srgb',srgb);tex.set_editor_property('compression_settings',compression)
    unreal.EditorAssetLibrary.save_loaded_asset(tex);textures[kind]=tex
mat=unreal.load_asset(P+'/M_AKM_Redwood') if unreal.EditorAssetLibrary.does_asset_exist(P+'/M_AKM_Redwood') else assets.create_asset('M_AKM_Redwood',P,unreal.Material,unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(mat)
def node(cls,**props):
    n=lib.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,b,slot):lib.connect_material_expressions(a,'',b,slot)
uv=node(unreal.MaterialExpressionTextureCoordinate, u_tiling=2.0,v_tiling=2.0)
samples={}
for kind,tex in textures.items():
    n=node(unreal.MaterialExpressionTextureSample,texture=tex)
    if kind=='NormalDX':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    elif kind=='Roughness':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    link(uv,n,'Coordinates');samples[kind]=n
tint=node(unreal.MaterialExpressionVectorParameter,parameter_name='RedwoodTint',default_value=unreal.LinearColor(1.6,.58,.32,1))
mul=node(unreal.MaterialExpressionMultiply);link(samples['Color'],mul,'A');link(tint,mul,'B')
lib.connect_material_property(mul,'',unreal.MaterialProperty.MP_BASE_COLOR)
rough=node(unreal.MaterialExpressionMultiply,const_b=.25);link(samples['Roughness'],rough,'A')
add=node(unreal.MaterialExpressionAdd,const_b=.24);link(rough,add,'A');lib.connect_material_property(add,'',unreal.MaterialProperty.MP_ROUGHNESS)
normal=node(unreal.MaterialExpressionLinearInterpolate,const_alpha=.18)
flat=node(unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(0,0,1,1));link(flat,normal,'A');link(samples['NormalDX'],normal,'B')
lib.connect_material_property(normal,'',unreal.MaterialProperty.MP_NORMAL)
lib.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
lib.layout_material_expressions(mat);lib.recompile_material(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
mesh=unreal.load_asset(P+'/SK_AKM_MannyNative');slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
    if str(s.material_slot_name)=='M_AKMR_Walnut':s.material_interface=mat;slots[i]=s
mesh.set_editor_property('materials',slots);assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
report={'source':'https://ambientcg.com/view?id=Wood051','license':'CC0','tint_linear':[1.6,.58,.32],'tiling':2,'normal_strength':.18,'roughness':'0.24 + map * 0.25','mesh':mesh.get_path_name(),'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in slots],'sha256':hashlib.sha256((O/'Redwood/Wood051_2K-JPG.zip').read_bytes()).hexdigest()}
(O/'Redwood/applied.json').write_text(json.dumps(report,indent=2));unreal.log('AKM_REDWOOD_PASS')
