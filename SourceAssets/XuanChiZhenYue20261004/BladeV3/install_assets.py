"""Import and save the blade revision through the existing UE writer queue."""
import json,runpy
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004/BladeV3'
V2='/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level_editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level_editor and level_editor.is_in_play_in_editor():raise RuntimeError('Finish PIE before importing the blade assets; no changes were made')
receipt={'complete':False,'assets':[],'game_tested':False}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));return obj
def imported(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj and options is None:return obj
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder;t.automated=True;t.replace_existing=options is not None;t.replace_existing_settings=options is not None;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+str(file))
    return obj
def node(m,cls,**kw):
    n=E.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material connection: '+target)
def prop(a,pin,p):
    if not E.connect_material_property(a,pin,p):raise RuntimeError('Material property: '+str(p))

textures={}
for ch in ['BaseColor','ORM','Normal','Relief']:
    t=imported(P/'Textures'/('Blade_'+ch+'.png'),'T_XuanChi_Blade_'+ch+'_V3',D+'/Textures')
    t.set_editor_property('srgb',ch=='BaseColor')
    t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_BC7 if ch=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    # These four narrow first-person maps lose the engraving completely in the
    # 16 x 64 mip tail. Keep their full mip chains resident only while loaded.
    t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if ch=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    t.set_editor_property('never_stream',True);t.set_editor_property('max_texture_size',4096);t.set_editor_property('lod_bias',0)
    t.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);t.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    if ch=='Normal':t.set_editor_property('flip_green_channel',True)
    textures[ch]=save(t)
name='M_XuanChi_SteelRelief_V3';m=u.load_asset(D+'/Materials/'+name)
if not m:m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(m)
m.set_editor_property('tangent_space_normal',True);m.set_editor_property('used_with_nanite',True)
uv=node(m,u.MaterialExpressionTextureCoordinate)
dx=node(m,u.MaterialExpressionDDX);dy=node(m,u.MaterialExpressionDDY)
link(uv,'',dx,'');link(uv,'',dy,'')
position=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
inputs={'UV':uv,'Position':position,'Camera':node(m,u.MaterialExpressionCameraPositionWS),
    'VertexNormal':node(m,u.MaterialExpressionVertexNormalWS),
    'DepthCm':node(m,u.MaterialExpressionScalarParameter,parameter_name='EngravingDepthCm',default_value=.016),
    'TextureSize':node(m,u.MaterialExpressionConstant2Vector,r=1024,g=4096),
    'ReliefTex':node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='Relief',texture=textures['Relief'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)}
pom=node(m,u.MaterialExpressionCustom,code=(P/'blade_relief_uv.ush').read_text(),
    description='Blade micro-parallax coordinates only; all native PBR samples share this UV',output_type=u.CustomMaterialOutputType.CMOT_FLOAT2)
fields=[]
for pin in inputs:
    field=u.CustomInput();field.set_editor_property('input_name',pin);fields.append(field)
pom.set_editor_property('inputs',fields)
for pin,src in inputs.items():link(src,'',pom,pin)
samples={}
for ch in ['BaseColor','Normal','ORM']:
    tx=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name=ch,texture=textures[ch],
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS,
        mip_value_mode=u.TextureMipValueMode.TMVM_DERIVATIVE,automatic_view_mip_bias=False)
    link(pom,'',tx,'');link(dx,'',tx,'DDX(UVs)');link(dy,'',tx,'DDY(UVs)');samples[ch]=tx
slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for src,pin,target,property in [(samples['BaseColor'],'RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),
    (samples['Normal'],'RGB','Normal',u.MaterialProperty.MP_NORMAL),
    (samples['ORM'],'G','Roughness',u.MaterialProperty.MP_ROUGHNESS),
    (samples['ORM'],'B','Metallic',u.MaterialProperty.MP_METALLIC)]:
    link(src,pin,slab,target);prop(src,pin,property)
prop(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
prop(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
E.layout_material_expressions(m)
errors=E.recompile_material(m)
if errors:raise RuntimeError('Blade material compilation: '+str(errors))
save(m)
hilt=u.load_asset(V2+'/Materials/M_XuanChi_Hilt_V2')
if not hilt:raise RuntimeError('Existing hilt material is required; do not replace its finish')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
for name in json.loads((P/'exports.json').read_text())['meshes']:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
    cfg=options.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    cfg.build_nanite=name!='SM_XuanChi_Blade_V3'
    mesh=imported(P/'Export'/(name+'.fbx'),name,D+'/Meshes',options)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,m if 'SteelRelief' in str(slot.material_slot_name) else hilt)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=name!='SM_XuanChi_Blade_V3'
    settings.explicit_tangents=True;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings);save(mesh)
dest=m.get_path_name().split('.')[0]+'_Whirlwind'
whirl=u.load_asset(dest) or L.duplicate_asset(m.get_path_name(),dest)
if not whirl:raise RuntimeError('UE could not create the sword skill material: '+dest)
if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(whirl)):
    out=node(whirl,u.MaterialExpressionTemporalResponsivenessOutput);one=node(whirl,u.MaterialExpressionConstant,r=1.);link(one,'',out,'')
E.recompile_material(whirl);save(whirl)
mapping_file=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping=json.loads(mapping_file.read_text(encoding='utf-8-sig'));mapping[m.get_path_name()]=whirl.get_path_name()
mapping_file.write_text(json.dumps(mapping,indent=2)+'\n')
receipt['complete']=True;(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
runpy.run_path(str(P/'publish_catalog.py'),run_name='__main__')
print('XUANCHI_BLADE_V3_ASSETS_AND_CATALOG_SAVED')
