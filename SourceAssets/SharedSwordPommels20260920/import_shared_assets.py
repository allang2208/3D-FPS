"""One editor import batch: common finish material, frost instances, adapter, icons."""
import unreal as u, json, shutil
from pathlib import Path
P=Path(__file__).parent; ROOT=P.parents[1]
D='/Game/Weapons/SharedSwordPommels20260920'
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor is None:
    raise RuntimeError('Open FPSGAME in the UE editor before importing shared pommel assets; a standalone game cannot import assets.')
if editor.is_in_play_in_editor():
    raise RuntimeError('End the active PIE session before importing the shared pommel assets.')
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
sources=json.loads((P.parent/'RuneSwordPommels20260920/import_receipt.json').read_text())
fit=json.loads((P/'frost_fit.json').read_text())
ids={'meteor':'ballast_hardened','jade_core':'ballast_rune','swift':'ballast_magic_orb'}
receipt={'materials':{},'finishes':{'frost_bronze':{}},'icons':[]}
def save(asset):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def node(mat,cls,**properties):
    result=M.create_material_expression(mat,cls)
    for key,value in properties.items():result.set_editor_property(key,value)
    return result
def connect(a,out,b,pin):
    if not M.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed: '+pin)
def output(a,pin,property):
    if not M.connect_material_property(a,pin,property):raise RuntimeError('Material output failed')
parent_path=D+'/Materials/M_SharedSwordPommel_MetalFinish'
parent=u.load_asset(parent_path) if L.does_asset_exist(parent_path) else A.create_asset('M_SharedSwordPommel_MetalFinish',D+'/Materials',u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(parent)
samples={}
for channel,path in sources[0]['textures'].items():
    sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel in ['BaseColor','Emissive'] else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    samples[channel]=node(parent,u.MaterialExpressionTextureSampleParameter2D,parameter_name=channel,texture=u.load_asset(path),sampler_type=sampler)
tint=node(parent,u.MaterialExpressionVectorParameter,parameter_name='MetalTint',default_value=u.LinearColor(1,1,1,1))
desaturate=node(parent,u.MaterialExpressionScalarParameter,parameter_name='MetalDesaturation',default_value=0.)
gray=node(parent,u.MaterialExpressionDesaturation)
connect(samples['BaseColor'],'RGB',gray,'');connect(desaturate,'',gray,'Fraction')
colored=node(parent,u.MaterialExpressionMultiply);connect(gray,'',colored,'A');connect(tint,'',colored,'B')
blend=node(parent,u.MaterialExpressionLinearInterpolate)
connect(samples['BaseColor'],'RGB',blend,'A');connect(colored,'',blend,'B');connect(samples['Metallic'],'R',blend,'Alpha')
output(blend,'',u.MaterialProperty.MP_BASE_COLOR)
output(samples['Metallic'],'R',u.MaterialProperty.MP_METALLIC)
rough_scale=node(parent,u.MaterialExpressionScalarParameter,parameter_name='RoughnessScale',default_value=1.)
rough=node(parent,u.MaterialExpressionMultiply);connect(samples['Roughness'],'R',rough,'A');connect(rough_scale,'',rough,'B');output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
output(samples['Normal'],'RGB',u.MaterialProperty.MP_NORMAL)
emission=node(parent,u.MaterialExpressionMultiply,const_b=3.);connect(samples['Emissive'],'RGB',emission,'A');output(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
M.layout_material_expressions(parent);M.recompile_material(parent);save(parent)
receipt['master_material']=parent.get_path_name()
for row in sources:
    key=row['id'];name='MI_SharedPommel_'+key+'_FrostBronze';path=D+'/Materials/'+name
    mi=u.load_asset(path) if L.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    M.set_material_instance_parent(mi,parent)
    for channel,texture in row['textures'].items():M.set_material_instance_texture_parameter_value(mi,channel,u.load_asset(texture))
    M.set_material_instance_vector_parameter_value(mi,'MetalTint',u.LinearColor(*fit['metal_tint'],1))
    M.set_material_instance_scalar_parameter_value(mi,'MetalDesaturation',fit['metal_desaturation'])
    M.set_material_instance_scalar_parameter_value(mi,'RoughnessScale',fit['roughness_scale'])
    M.update_material_instance(mi);save(mi)
    mesh=u.load_asset(row['asset'])
    overrides={str(s.material_slot_name):mi.get_path_name() for s in mesh.static_materials if '_Opaque' in str(s.material_slot_name)}
    if not overrides:raise RuntimeError('No opaque material slot: '+row['asset'])
    receipt['finishes']['frost_bronze'][ids[key]]={'materials':overrides}
    receipt['materials'][key]=mi.get_path_name()
    print('SHARED_POMMEL_FINISH_SAVED',mi.get_path_name())

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task=u.AssetImportTask();task.filename=str(P/'Export/SM_SwordPommel_FrostAdapter.fbx');task.destination_path=D+'/Interfaces';task.destination_name='SM_SwordPommel_FrostAdapter'
task.automated=True;task.replace_existing=True;task.save=False;task.options=options
A.import_asset_tasks([task])
adapter=u.load_asset(D+'/Interfaces/SM_SwordPommel_FrostAdapter')
if not adapter or not task.imported_object_paths:raise RuntimeError('Adapter import failed')
collar=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
if not collar:raise RuntimeError('Frost collar material unavailable')
for index in range(len(adapter.static_materials)):adapter.set_material(index,collar)
save(adapter);receipt['adapter']=adapter.get_path_name()
backup=P/'BeforeShared';backup.mkdir(exist_ok=True)
icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
for key in ids.values():
    name='ue_frost_crystal_sword_pommel_'+key
    target=icons/(name+'.png')
    for prior in [target,target.with_suffix('.uasset')]:
        if prior.exists() and not (backup/prior.name).exists():shutil.copy2(prior,backup/prior.name)
    shutil.copy2(P/'Icons'/target.name,target)
    path='/Game/ColdSteelData/AttachmentIcons20260913/'+name
    result=u.ModelingService.import_texture(str(target),path,True,'Default',True)
    if not result.success:raise RuntimeError(result.message)
    texture=u.load_asset(path)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(texture);receipt['icons'].append(texture.get_path_name())
receipt['testing']='Not run; production icons only.'
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('SHARED_SWORD_POMMEL_ASSETS_SAVED',adapter.get_path_name())
