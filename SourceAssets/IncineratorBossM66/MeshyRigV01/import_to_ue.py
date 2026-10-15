"""Import and save M66's completed rig through the existing editor connection."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/MeshyRigV01')
DEST='/Game/Monsters/IncineratorBossM66';VERSION=DEST+'/RigV01'
manifest=json.loads((ROOT/'Records/rig_completion.json').read_text(encoding='utf-8'))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
REPORT=ROOT/'Records/ue_import.json'
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'saved':[],'runtime_tested':False}
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('M66 import requires PIE to end; no assets were changed')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 target packages have unsaved changes; preserved without overwriting')

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def create(name,path,cls,factory):
    return u.load_asset(path+'/'+name) if E.does_asset_exist(path+'/'+name) else A.create_asset(name,path,cls,factory)
def import_file(filename,name,path,options=None,factory=None):
    if E.does_asset_exist(path+'/'+name):return u.load_asset(path+'/'+name)
    task=u.AssetImportTask();task.filename=filename;task.destination_name=name;task.destination_path=path
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options
    if factory:task.factory=factory
    A.import_asset_tasks([task]);asset=u.load_asset(path+'/'+name)
    if not asset:raise RuntimeError('Missing imported asset '+path+'/'+name)
    return asset

old_fbx=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=True
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True
    data.force_front_x_axis=True;data.import_uniform_scale=1.
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(manifest['fbx'],'SK_M66_BackCompleted',VERSION,options,u.FbxFactory())
    for asset in [mesh,mesh.skeleton,mesh.physics_asset]:
        if asset:save(asset)
    textures={}
    for key,filename in manifest['textures'].items():
        tex=import_file(filename,'T_M66_'+key,VERSION+'/Textures')
        tex.set_editor_property('srgb',key=='BaseColor')
        if key=='Normal':
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property('flip_green_channel',True)
        elif key=='MetallicRoughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(tex);textures[key]=tex
    mat=create('M_M66_Body',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True);mat.set_editor_property('used_with_skeletal_mesh',True)
    slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for key,pin,prop,channel in [('BaseColor','BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),
        ('Normal','Normal',u.MaterialProperty.MP_NORMAL,'RGB'),
        ('MetallicRoughness','Roughness',u.MaterialProperty.MP_ROUGHNESS,'G'),
        ('MetallicRoughness','Metallic',u.MaterialProperty.MP_METALLIC,'B')]:
        sample=ME.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.texture=textures[key]
        sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
        ME.connect_material_property(sample,channel,prop);ME.connect_material_expressions(sample,channel,slab,pin)
    ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(mat);save(mat)
    slots=list(mesh.materials)
    for slot in slots:slot.material_interface=mat
    mesh.set_editor_property('materials',slots)
    E.set_metadata_tag(mesh,'M66.Source','User decimated SmartRig GLB; original topology, UVs and 74 bones retained')
    E.set_metadata_tag(mesh,'M66.BackRig','88 authoring bones: ground root, posterior anchor, four sac controls, four two-bone vent chains')
    E.set_metadata_tag(mesh,'M66.Stage','Rig only; no movement, attacks, or encounter authored')
    save(mesh)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Character)
    bp=create('BP_M66RigPreview',DEST,u.Blueprint,factory)
    defaults=u.get_default_object(bp.generated_class())
    defaults.set_editor_property('replicates',True)
    defaults.set_editor_property('replicate_movement',True)
    defaults.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
    defaults.set_editor_property('tags',[u.Name('M66'),u.Name('RigPreview')])
    capsule=defaults.get_editor_property('capsule_component');capsule.set_capsule_size(90.,190.,False)
    component=defaults.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
    component.set_editor_property('relative_location',u.Vector(0.,0.,-190.))
    component.set_editor_property('relative_rotation',u.Rotator(0.,0.,0.))
    component.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    component.set_collision_profile_name('CharacterMesh')
    movement=defaults.get_editor_property('character_movement')
    movement.set_editor_property('max_walk_speed',0.)
    movement.set_editor_property('max_step_height',40.)
    E.set_metadata_tag(bp,'M66.Stage','User model import and back skin completion; static rig preview, no combat')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
        'physics_asset':mesh.physics_asset.get_path_name() if mesh.physics_asset else None,
        'material':mat.get_path_name(),'blueprint':bp.get_path_name(),
        'height_m':3.8,'front_axis':'ForceFrontXAxis at import; actor mesh yaw 0',
        'animations':[],'physics':'Importer-generated reference bodies; no dedicated ragdoll authored',
        'development_entry':'IncineratorBossM66Rig / 焚骸 M-66（模型绑定）',
        'complete':True})
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M66_IMPORT_SAVED '+json.dumps(report,ensure_ascii=False))
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old_fbx))
