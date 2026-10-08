"""Create independent V2 assets in the current editor or a background commandlet."""
import json,runpy,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2';OLD='/Game/Weapons/XuanChiZhenYue20261004'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt={'complete':False,'assets':[],'game_tested':False}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));return obj
def imported(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj:return obj
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder;t.automated=True;t.replace_existing=False;t.save=False
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
for family in ['Hilt','Blade']:
    textures[family]={}
    for ch in ['BaseColor','ORM','Normal']+(['Relief'] if family=='Blade' else []):
        t=imported(P/'Textures'/(family+'_'+ch+'.png'),'T_XuanChi_'+family+'_'+ch+'_V2',D+'/Textures')
        t.set_editor_property('srgb',ch=='BaseColor');t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_BC7 if ch=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        t.set_editor_property('never_stream',False)
        if ch=='Normal':t.set_editor_property('flip_green_channel',True)
        if family=='Blade':t.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);t.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        textures[family][ch]=save(t)
materials={}
for family in ['Hilt','Tassel','Mount']:
    name='M_XuanChi_'+family+'_V2';m=u.load_asset(D+'/Materials/'+name)
    if not m:m=L.duplicate_asset(OLD+'/Materials/M_XuanChi_'+family,D+'/Materials/'+name)
    for n in E.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionTextureSample):
            old=n.get_editor_property('texture')
            if old:
                for ch,t in textures['Hilt'].items():
                    if old.get_name().endswith('_'+ch):n.set_editor_property('texture',t)
        elif family=='Mount' and isinstance(n,u.MaterialExpressionConstant3Vector):n.set_editor_property('constant',u.LinearColor(.150,.165,.175,1))
    E.recompile_material(m);materials[family]=save(m)
name='M_XuanChi_SteelRelief_V2';m=u.load_asset(D+'/Materials/'+name)
if not m:
    m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('tangent_space_normal',True);m.set_editor_property('used_with_nanite',True)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    pos=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    size=node(m,u.MaterialExpressionConstant2Vector,r=1024,g=4096)
    inputs={'UV':uv,'Position':pos,'Camera':node(m,u.MaterialExpressionCameraPositionWS),'VertexNormal':node(m,u.MaterialExpressionVertexNormalWS),'DepthCm':node(m,u.MaterialExpressionScalarParameter,parameter_name='EngravingDepthCm',default_value=.032),'TextureSize':size}
    for ch,pin in [('BaseColor','ColorTex'),('ORM','ORMTex'),('Normal','NormalTex'),('Relief','ReliefTex')]:
        inputs[pin]=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name=ch,texture=textures['Blade'][ch],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    shader=node(m,u.MaterialExpressionCustom,code=(P/'steel_relief.ush').read_text(),description='Bounded physical-depth steel engraving; shared UV for every PBR channel',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    fields=[]
    for pin in inputs:
        x=u.CustomInput();x.set_editor_property('input_name',pin);fields.append(x)
    shader.set_editor_property('inputs',fields)
    outputs=[]
    for pin,width in [('NormalTangent',3),('AO',1),('Metallic',1)]:
        x=u.CustomOutput();x.set_editor_property('output_name',pin);x.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));outputs.append(x)
    shader.set_editor_property('additional_outputs',outputs)
    for pin,src in inputs.items():link(src,'',shader,pin)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for channels,pin,property in [('rgb','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('a','Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
        mask=node(m,u.MaterialExpressionComponentMask,**{k:k in channels for k in 'rgba'});link(shader,'',mask,'');link(mask,'',slab,pin);prop(mask,'',property)
    link(shader,'NormalTangent',slab,'Normal');prop(shader,'NormalTangent',u.MaterialProperty.MP_NORMAL)
    link(shader,'Metallic',slab,'Metallic');prop(shader,'Metallic',u.MaterialProperty.MP_METALLIC);prop(shader,'AO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    prop(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);E.layout_material_expressions(m)
errors=E.recompile_material(m)
if errors:raise RuntimeError('Steel relief shader: '+str(errors))
materials['Blade']=save(m)
# FBX legacy importer preserves the authored final corner normals and both UV domains.
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
data=json.loads((P/'exports.json').read_text())
for name in data['meshes']:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
    cfg=options.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False;cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;cfg.build_nanite=name!='SM_XuanChi_Blade_V2'
    mesh=imported(P/'Export'/(name+'.fbx'),name,D+'/Meshes',options)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials['Blade' if 'SteelRelief' in str(slot.material_slot_name) else 'Hilt'])
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=name!='SM_XuanChi_Blade_V2';settings.explicit_tangents=True;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings);save(mesh)
mapping_file=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json';extra={}
for family,src in materials.items():
    dest=src.get_path_name().split('.')[0]+'_Whirlwind';m=u.load_asset(dest)
    if not m:
        m=L.duplicate_asset(src.get_path_name(),dest);out=node(m,u.MaterialExpressionTemporalResponsivenessOutput);one=node(m,u.MaterialExpressionConstant,r=1.);link(one,'',out,'');E.recompile_material(m)
    save(m);extra[src.get_path_name()]=m.get_path_name()
mapping=json.loads(mapping_file.read_text(encoding='utf-8-sig'));mapping.update(extra);mapping_file.write_text(json.dumps(mapping,indent=2)+'\n')
icon=P/'ue_xuanchi_zhenyue_v2.png'
if icon.exists():
    dest=ROOT/'Content/ColdSteelData/Icons'/icon.name;shutil.copy2(icon,dest)
    tex=imported(dest,icon.stem,'/Game/ColdSteelData/Icons');tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);tex.set_editor_property('never_stream',True);tex.set_editor_property('srgb',True);save(tex)
    receipt['inventory_icon']='Icons/'+icon.name
receipt['complete']=True;(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));runpy.run_path(str(P/'publish_catalog.py'),run_name='__main__')
print('XUANCHI_SURFACE_V2_ASSETS_AND_CATALOG_SAVED')
