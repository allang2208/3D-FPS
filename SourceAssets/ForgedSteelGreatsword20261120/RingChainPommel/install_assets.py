"""Import the ring counterweight, its surface maps and rigid-link WPO materials."""
import json
from pathlib import Path
import runpy
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[2]
stage=project/'Saved/ForgedSteelGreatsword20261120/RingChainHost'
host=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if host!=stage:
    raise RuntimeError('Use the isolated RingChainHost authoring project')
folder='/Game/Weapons/ForgedSteelGreatsword20261120/RingChainPommel'
icon_folder='/Game/ColdSteelData/AttachmentIcons20260913'
icon_key='ue_forged_steel_greatsword_pommel_ring_chain_pommel'
mesh_name='SM_ForgedSteelGreatsword_RingChainPommel'
spec=json.loads((here/'dynamics.json').read_text(encoding='utf-8'))
import_asset=runpy.run_path(str(here.parent/'CommonMods/install_legendary_blade.py'))['import_asset']
graph=runpy.run_path(str(project/'SourceAssets/KukriRefinement20261027/hanging_material.py'))
node,connect,output,custom,transform=[graph[k] for k in ('node','link','out','custom','transform')]
lib=u.MaterialEditingLibrary
assets=[]
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Failed to save '+obj.get_path_name())
    assets.append(obj.get_path_name())

maps={}
for channel in ('BaseColor','ORM','Normal'):
    name='T_RingChain_'+channel
    texture=import_asset(here/(name+'.png'),folder,name)
    texture.set_editor_properties({'srgb':channel=='BaseColor','lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON,
        'compression_settings':{'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,
         'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[channel]})
    maps[channel]=texture
    save(texture)

def make_material(name,articulated):
    m=u.load_asset(folder+'/'+name) if u.EditorAssetLibrary.does_asset_exist(folder+'/'+name) else None
    if not m:m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    m.set_editor_property('tangent_space_normal',not articulated)
    types={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
           'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}
    tex={key:node(m,u.MaterialExpressionTextureSample,texture=value,sampler_type=types[key]) for key,value in maps.items()}
    normal=tex['Normal'];normal_pin='RGB'
    if articulated:
        active=node(m,u.MaterialExpressionScalarParameter,parameter_name='TasselActive',default_value=0.)
        skin=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=spec['skin_uv_channel'])
        bindings=[('Skin',skin,''),('Active',active,'')]
        for i,rest in enumerate(spec['guides_cm'][:7]):
            rest_color=u.LinearColor(*rest,0)
            r=node(m,u.MaterialExpressionConstant3Vector,constant=rest_color)
            p=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselP'+str(i),default_value=rest_color)
            q=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselQ'+str(i),default_value=u.LinearColor(0,0,0,1))
            quat=node(m,u.MaterialExpressionAppendVector);connect(q,'RGB',quat,'A');connect(q,'A',quat,'B')
            bindings.extend([('R'+str(i),r,''),('P'+str(i),p,'RGB'),('Q'+str(i),quat,'')])
        preamble=('int i=clamp((int)round(Skin.x),0,6); '
                  'float4 qs[7]={Q0,Q1,Q2,Q3,Q4,Q5,Q6}; float4 q=qs[i]; ')
        world=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        loc=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                 transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        connect(world,'',loc,'')
        displace=custom(m,preamble+'float3 rest[7]={R0,R1,R2,R3,R4,R5,R6}; float3 p[7]={P0,P1,P2,P3,P4,P5,P6}; '
                        'float3 v=V-rest[i]; return (p[i]+v+2*cross(q.xyz,cross(q.xyz,v)+q.w*v)-V)*Active;',
                        bindings+[('V',loc,'')])
        offset=transform(m,displace,'',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                         u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        output(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        local_normal=transform(m,normal,'RGB',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                               u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
        normal_inputs=[b for b in bindings if b[0]=='Skin' or b[0]=='Active' or b[0].startswith('Q')]
        deformed=custom(m,preamble+'return normalize(V+2*cross(q.xyz,cross(q.xyz,V)+q.w*V)*Active);',
                        normal_inputs+[('V',local_normal,'')])
        normal=transform(m,deformed,'',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                         u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        normal_pin=''
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for src,pin,prop,slot in [(tex['BaseColor'],'RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),
                              (tex['ORM'],'G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
                              (tex['ORM'],'B',u.MaterialProperty.MP_METALLIC,'Metallic'),
                              (normal,normal_pin,u.MaterialProperty.MP_NORMAL,'Normal')]:
        connect(src,pin,slab,slot);output(src,pin,prop)
    output(tex['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);output(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    lib.layout_material_expressions(m)
    errors=lib.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m)
    return m

materials={name:make_material(name,name.endswith('Links')) for name in ('M_RingChain_Socket','M_RingChain_Links')}
worlds=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.SystemLibrary.execute_console_command(worlds.get_editor_world() if worlds else None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh=True
options.import_as_skeletal=options.import_animations=options.import_materials=options.import_textures=False
settings=options.static_mesh_import_data
settings.combine_meshes=True
settings.auto_generate_collision=settings.generate_lightmap_u_vs=settings.build_nanite=False
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=import_asset(here/(mesh_name+'.fbx'),folder,mesh_name,options)
for index,slot in enumerate(mesh.static_materials):
    mesh.set_material(index,materials[str(slot.material_slot_name)])
save(mesh)
icon=import_asset(project/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_key+'.png'),icon_folder,icon_key)
icon.set_editor_properties({'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
    'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'never_stream':True,'srgb':True})
save(icon)
(stage/'import_receipt.json').write_text(json.dumps({'complete':True,'assets':assets},indent=2)+'\n',encoding='utf-8')
