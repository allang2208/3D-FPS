"""Save shared static heads/PBR and then merge their runtime catalog entries."""
import unreal as u,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];D='/Game/Weapons/CommonHammerHeads20261014'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before importing these new parts')
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name().startswith(D+'/'):raise RuntimeError('Unsaved shared hammer-head package: '+pkg.get_name())
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt={'complete':False,'assets':[],'tested':False}
def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Asset save failed: '+str(asset))
    receipt['assets'].append(asset.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def imp(file,name,folder,options=None):
    asset=u.load_asset(folder+'/'+name)
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+str(file))
    return asset
source={key:u.load_asset('/Game/Weapons/SteelWarhammer20261014/Textures/T_SteelWarhammer_'+key) for key in ('BaseColor','MetallicRoughness','Normal')}
factory=u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface')
if not factory or any(not tex for tex in source.values()):raise RuntimeError('Original steel surface unavailable')
new={}
for key in source:
    tex=imp(P/'Textures'/(key+'.png'),'T_CommonHammerSteel_'+key,D+'/Textures')
    tex.set_editor_property('srgb',key=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='MetallicRoughness' else u.TextureCompressionSettings.TC_DEFAULT)
    if key=='Normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);new[key]=tex
material=u.load_asset(D+'/Materials/M_CommonHammerHeadSteel')
if not material:
    material=A.create_asset('M_CommonHammerHeadSteel',D+'/Materials',u.Material,u.MaterialFactoryNew())
    material.set_editor_property('use_material_attributes',False);material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('used_with_skeletal_mesh',False)
    surface=E.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,500,0)
    surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    color=E.create_material_expression(material,u.MaterialExpressionVertexColor,-800,600)
    samples=[]
    for index,bank in enumerate((source,new)):
        uv=E.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-900,index*300);uv.set_editor_property('coordinate_index',index)
        group={}
        for key,tex in bank.items():
            node=E.create_material_expression(material,u.MaterialExpressionTextureSample,-650,index*650+len(group)*180);node.set_editor_property('texture',tex)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            E.connect_material_expressions(uv,'',node,'UVs');group[key]=node
        samples.append(group)
    for key,channel,pin,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('MetallicRoughness','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),
                                ('MetallicRoughness','B','Metallic',u.MaterialProperty.MP_METALLIC),('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
        mix=E.create_material_expression(material,u.MaterialExpressionLinearInterpolate,-100,0)
        E.connect_material_expressions(samples[0][key],channel,mix,'A');E.connect_material_expressions(samples[1][key],channel,mix,'B');E.connect_material_expressions(color,'R',mix,'Alpha')
        output=mix
        if key=='Normal':
            output=E.create_material_expression(material,u.MaterialExpressionNormalize,180,450);E.connect_material_expressions(mix,'',output,'VectorInput')
        if not E.connect_material_expressions(output,'',surface,pin):raise RuntimeError('Substrate input: '+pin)
        E.connect_material_property(output,'',prop)
    if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Missing Substrate output')
    E.layout_material_expressions(material)
    errors=list(E.recompile_material(material))
    if errors:raise RuntimeError('Material compile: '+str(errors))
save(material)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
for row in rows:
    mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D,opt)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name)
        if 'CommonHammerHeadSteel' in name:mesh.set_material(i,material)
        elif 'SteelWarhammerSurface' in name:mesh.set_material(i,factory)
        else:raise RuntimeError('Unknown head material: '+name)
    save(mesh)
for row in rows:
    key='hammer_heads_'+row['id'];file=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
    if file.exists():
        tex=imp(file,key,'/Game/ColdSteelData/AttachmentIcons20260913');tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
runpy.run_path(str(P/'register_heads.py'))
receipt['complete']=True;(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
