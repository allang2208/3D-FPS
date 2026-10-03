"""Background production import: M07 mesh, PBR tissue, cloth and breathing source.
No world, viewport, PIE, screenshot, navigation build or runtime test is used.
"""
import unreal as u
import json
from pathlib import Path

if not hasattr(u, 'BlindSupplicantAuthoring'):
    raise RuntimeError('The M07 native authoring class is not available. Complete the FPSGAMEEditor build before importing M07 assets.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level_editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level_editor and level_editor.is_in_play_in_editor():
        raise RuntimeError('M07 asset authoring must finish outside PIE; existing dirty cloth data is preserved')

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
DEST='/Game/Monsters/BlindSupplicantM07'
REPORT=ROOT/'ue_delivery.json'
class M07SavedStage(Exception):
    pass

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=ROOT.parent.parent/'FPSGAME.uproject':
    raise RuntimeError('This authoring script must run in FPSGAME')
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'completed':[],'assets':[],'tested':False}
report['background_import_executed']=True
report['execution_mode']=globals().get('M07_EXECUTION_MODE','background_commandlet')

def record(stage,receipt=None):
    if stage not in report['completed']:report['completed'].append(stage)
    if receipt:report[stage]=receipt
    report['stage']='saved_'+stage
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M07 SAVED '+stage,flush=True)
    if globals().get('M07_STOP_AFTER')==stage:
        raise M07SavedStage(stage)
def save(asset):
    if not asset or not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Asset outside M07 write scope')
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('M07 package save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:report['assets'].append(asset.get_path_name())

def import_file(file,name,path,options=None,factory=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=path;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    if options:task.options=options
    if factory:task.factory=factory
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('M07 import produced no object: '+str(file))
    asset=u.load_asset(path+'/'+name)
    if not asset:raise RuntimeError('M07 imported asset is unavailable '+path+'/'+name)
    return asset

textures={}
if 'textures' not in report['completed']:
    for key,file,normal in [('base','M07_basecolor_source.jpg',False),('rough','M07_roughness.png',False),
                            ('metal','M07_metallic.png',False),('normal','M07_normal_source.jpg',True)]:
        tex=import_file(ROOT/'Textures'/file,'T_M07_'+key,DEST+'/Textures',factory=u.TextureFactory())
        tex.set_editor_property('srgb',key=='base')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if key=='base' else u.TextureCompressionSettings.TC_MASKS)
        if normal:tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[key]=tex
    record('textures')
else:
    textures={key:u.load_asset(DEST+'/Textures/T_M07_'+key) for key in ['base','rough','metal','normal']}

materials={}

def enable_material_usage(mat,membrane):
    # UE 5.8 stores usage through SetUsageByFlag; the legacy reflected
    # used_with_* fields are deprecated. This editor API also recompiles
    # the material when a usage changes, including in a headless commandlet.
    MEL.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    if membrane:MEL.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_CLOTHING,True)

def tissue_material(name,membrane):
    path=DEST+'/Materials/'+name
    mat=u.load_asset(path) if LIB.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if membrane else u.BlendMode.BLEND_OPAQUE)
    if membrane:mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for key,prop,pin in [('base',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),('rough',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
                          ('metal',u.MaterialProperty.MP_METALLIC,'Metallic'),('normal',u.MaterialProperty.MP_NORMAL,'Normal')]:
        node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',textures[key])
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='base' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        output='RGB' if key in ['base','normal'] else 'R'
        if not MEL.connect_material_property(node,output,prop):raise RuntimeError('M07 texture link failed '+key)
        if not MEL.connect_material_expressions(node,output,slab,pin):raise RuntimeError('M07 Substrate texture link failed '+pin)
    if membrane:
        opacity=MEL.create_material_expression(mat,u.MaterialExpressionScalarParameter)
        opacity.set_editor_property('parameter_name','TissueOpacity');opacity.set_editor_property('default_value',.78)
        MEL.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
        MEL.connect_material_expressions(opacity,'',slab,'Opacity')
    if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('M07 Substrate output link failed')
    enable_material_usage(mat,membrane)
    MEL.recompile_material(mat);save(mat);return mat

if 'materials' not in report['completed']:
    materials['M07_Body']=tissue_material('M07_Body',False)
    for i in range(1,7):materials[f'M07_Gill_{i:02d}']=tissue_material(f'M07_Gill_{i:02d}',True)
    record('materials')
else:
    materials={name:u.load_asset(DEST+'/Materials/'+name) for name in ['M07_Body']+[f'M07_Gill_{i:02d}' for i in range(1,7)]}

# Keep this separate from material graph creation so an interrupted import,
# or assets saved by the earlier script, can resume without recreating PBR.
if 'material_usage' not in report['completed']:
    usage_receipt=[]
    for name,mat in materials.items():
        if not mat:raise RuntimeError('M07 material unavailable for usage authoring '+name)
        membrane=name.startswith('M07_Gill_')
        enable_material_usage(mat,membrane)
        save(mat)
        usage_receipt.append({'asset':mat.get_path_name(),'skeletal_mesh':True,'clothing':membrane})
    record('material_usage',{'saved':True,'materials':usage_receipt})

def fbx_options(skeleton=None,animation=False):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=True;o.import_mesh=not animation;o.import_animations=animation
    o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
    if skeleton:o.skeleton=skeleton
    data=o.anim_sequence_import_data if animation else o.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
    if animation:
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
        data.set_editor_property('update_skeleton_reference_pose',False)
    return o

def bind_materials(mesh):
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        if name in materials:slot.material_interface=materials[name]
    mesh.set_editor_property('materials',slots)

mesh=u.load_asset(DEST+'/SK_M07')
if 'mesh_source' not in report['completed']:
    mesh=import_file(ROOT/'Delivery/SK_M07_ClothBuildSource.fbx','SK_M07',DEST,fbx_options(),u.FbxFactory())
    bind_materials(mesh)
    LIB.set_metadata_tag(mesh,'Source','User Meshy web GLB; source-preserving identity partitions plus whole-body anatomy source')
    LIB.set_metadata_tag(mesh,'Status','First authoring pass; semantic seams, fitting, motion and runtime remain user review')
    save(mesh);save(mesh.skeleton);record('mesh_source')

if 'cloth_extracted' not in report['completed']:
    if not mesh:raise RuntimeError('Saved SK_M07 could not be loaded for cloth authoring')
    receipt=json.loads(u.BlindSupplicantAuthoring.build_gill_cloth(mesh,str(ROOT/'Authoring/cloth_ue_manifest.json'),False))
    if not receipt.get('success',False) and receipt.get('stage')=='saved_cloth':
        receipt=json.loads(u.BlindSupplicantAuthoring.build_gill_cloth(mesh,str(ROOT/'Authoring/cloth_ue_manifest.json'),True))
        receipt['production_route']='extract_source_proxies'
    else:
        receipt['production_route']='resume_existing_saved_cloth'
    if not receipt.get('success',False):raise RuntimeError('M07 cloth extraction failed: '+json.dumps(receipt,ensure_ascii=False))
    report['pending_cloth_extraction']=receipt
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save(mesh);receipt['saved']=True;receipt['caller_must_save_package']=False
    report.pop('pending_cloth_extraction',None);record('cloth_extracted',receipt)

if 'display_cloth' not in report['completed']:
    mesh=import_file(ROOT/'Delivery/SK_M07_Display.fbx','SK_M07',DEST,fbx_options(mesh.skeleton),u.FbxFactory())
    bind_materials(mesh)
    receipt=json.loads(u.BlindSupplicantAuthoring.build_gill_cloth(mesh,str(ROOT/'Authoring/cloth_ue_manifest.json'),False))
    if not receipt.get('success',False):raise RuntimeError('M07 display cloth binding failed: '+json.dumps(receipt,ensure_ascii=False))
    LIB.set_metadata_tag(mesh,'Cloth','Six separate shoulder/back-pinned living membrane assets; independent assets have no cross-panel collision')
    save(mesh);save(mesh.skeleton);receipt['saved']=True;receipt['caller_must_save_package']=False;record('display_cloth',receipt)

if 'breathing_source' not in report['completed']:
    clip=import_file(ROOT/'Delivery/A_M07_GillBreathing_Source.fbx','A_M07_GillBreathing_Source',DEST+'/Animations',fbx_options(mesh.skeleton,True),u.FbxFactory())
    LIB.set_metadata_tag(clip,'Role','4-second dedicated gill-chain source breathing loop; no humanoid locomotion or gameplay')
    save(clip);save(mesh.skeleton);record('breathing_source')
report['stage']='M07 separate mesh, tissue PBR, six cloth assets and source breathing saved'
report.pop('blocker',None)
report['ue_imported']=True;report['cloth_assets_saved_in_ue']=True
report['gameplay_integrated']=False;report['f6_registered']=False;report['tested']=False
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M07 BACKGROUND AUTHORING SAVED; NO GAMEPLAY TEST',flush=True)
