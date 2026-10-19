"""Import the selected Meshy weapon and save only the new Zhanmadao packages."""
import json, runpy
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
EX=json.loads((P/'exports.json').read_text(encoding='utf-8'));D=EX['ue_root']
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before asset import')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt={'complete':False,'assets':[],'game_tested':False,'visual_accepted':False}
def save(obj):
    if not obj or not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+str(obj))
    path=obj.get_path_name()
    if path not in receipt['assets']:receipt['assets'].append(path)
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return obj
def imp(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj:return obj
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.replace_existing=False;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);obj=u.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+str(file))
    return obj
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D+'/'):raise RuntimeError('Unsaved target package: '+package.get_name())

textures={}
for channel in ['BaseColor','MetallicRoughness','Normal']:
    t=imp(P/'Textures'/('Zhanmadao_'+channel+'.jpg'),'T_Zhanmadao_'+channel+'_V1',D+'/Textures')
    t.set_editor_property('srgb',channel=='BaseColor')
    t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_BC7 if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    t.set_editor_property('never_stream',False)
    if channel=='Normal':t.set_editor_property('flip_green_channel',True)
    textures[channel]=save(t)

name='M_Zhanmadao_Surface_V1';material=u.load_asset(D+'/Materials/'+name)
if not material:
    material=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    material.set_editor_property('two_sided',True)
    material.set_editor_property('used_with_nanite',True)
    material.set_editor_property('used_with_skeletal_mesh',False)
    surface=E.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,400,0)
    surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    samples={}
    for i,channel in enumerate(['BaseColor','MetallicRoughness','Normal']):
        sample=E.create_material_expression(material,u.MaterialExpressionTextureSample,-350,i*200)
        sample.set_editor_property('texture',textures[channel])
        sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        samples[channel]=sample
    for channel,pin,target,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('MetallicRoughness','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),('MetallicRoughness','B','Metallic',u.MaterialProperty.MP_METALLIC),('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
        if not E.connect_material_expressions(samples[channel],pin,surface,target):raise RuntimeError('Substrate input: '+target)
        if not E.connect_material_property(samples[channel],pin,prop):raise RuntimeError('Material input: '+target)
    if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Front material output')
    E.layout_material_expressions(material)
    errors=list(E.recompile_material(material))
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
save(material)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in [r['mesh'] for r in EX['parts']]+[EX['world_mesh']]:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False
    opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    cfg=opt.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    cfg.build_nanite=True
    mesh=imp(P/'Export'/(name+'.fbx'),name,D+'/Meshes',opt)
    for i in range(len(mesh.static_materials)):mesh.set_material(i,material)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True;settings.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',settings);save(mesh)

# Existing whirlwind presentation consumes this map for its temporal response.
dest=D+'/Materials/M_Zhanmadao_Surface_V1_Whirlwind'
whirl=u.load_asset(dest) or L.duplicate_asset(material.get_path_name(),dest)
if not whirl:raise RuntimeError('Whirlwind material creation failed')
if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(whirl)):
    out=E.create_material_expression(whirl,u.MaterialExpressionTemporalResponsivenessOutput)
    one=E.create_material_expression(whirl,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
    if not E.connect_material_expressions(one,'',out,''):raise RuntimeError('Whirlwind temporal output')
    errors=list(E.recompile_material(whirl))
    if errors:raise RuntimeError('Whirlwind material compilation failed: '+str(errors))
save(whirl)

icons=[(P/'Export/ue_zhanmadao.png','ue_zhanmadao','/Game/ColdSteelData/Icons')]
for row in EX['parts']:
    for key in ['ue_zhanmadao_category_'+row['slot'],'ue_zhanmadao_'+row['slot']+'_false']:
        icons.append((P/'Icons'/(row['slot']+'.png'),key,'/Game/ColdSteelData/AttachmentIcons20260913'))
for file,name,folder in icons:
    icon=imp(file,name,folder)
    icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True);save(icon)
receipt['complete']=True;receipt['rigid_length_cm']=EX['reference']['rigid_length_cm']
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
runpy.run_path(str(P/'publish_catalog.py'),run_name='__main__')
print('ZHANMADAO_ASSETS_AND_CATALOG_SAVED',flush=True)
