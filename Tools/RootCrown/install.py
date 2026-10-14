"""Import and inspect only the Root Crown rig-stage assets in the background."""
import json, traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/RigV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing','saved':[],'gameplay_implemented':False,'pie_run':False}
RECEIPT=ROOT/'Reports/ue-import.json'
def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    if not asset or not LIB.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+str(asset))
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def create(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) if LIB.does_asset_exist(folder+'/'+name) else AT.create_asset(name,folder,cls,factory)
def import_file(path,name,folder,options=None,factory=None):
    if LIB.does_asset_exist(folder+'/'+name):return u.load_asset(folder+'/'+name)
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options
    if factory:task.factory=factory
    AT.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import missing: '+folder+'/'+name)
    return asset
def fbx(animation=False,skeleton=None):
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_as_skeletal=True;opts.import_mesh=not animation;opts.import_animations=animation
    opts.import_materials=False;opts.import_textures=False
    if skeleton:opts.skeleton=skeleton
    data=opts.anim_sequence_import_data if animation else opts.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    if animation:
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        opts.create_physics_asset=True
    return opts
def pose_at(clip,mesh,t):
    options=u.AnimPoseEvaluationOptions();options.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    options.set_editor_property('optional_skeletal_mesh',mesh)
    return u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
def align_root_units(clip,mesh):
    pose=pose_at(clip,mesh,0.);root=u.AnimPoseExtensions.get_bone_names(pose)[0]
    ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    first=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    target=ref.scale3d;old=first.scale3d
    if max(abs(target.x-old.x),abs(target.y-old.y),abs(target.z-old.z))>1e-5:
        count=clip.get_editor_property('data_model_interface').get_number_of_keys()
        positions=[];rotations=[];scales=[]
        for i in range(count):
            pose=pose_at(clip,mesh,clip.get_play_length()*i/max(1,count-1))
            x=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
            positions.append(x.translation);rotations.append(x.rotation);scales.append(target)
        c=clip.get_editor_property('controller');c.open_bracket('Preserve Root Crown FBX reference units',False)
        try:
            if not c.set_bone_track_keys(root,positions,rotations,scales,False):raise RuntimeError('Root track repair failed')
        finally:c.close_bracket(False)
    return {'root':str(root),'before':[old.x,old.y,old.z],'reference':[target.x,target.y,target.z]}
record()
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve it before asset integration')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Root Crown has unsaved target packages')
    mesh=import_file(ROOT/'Exports/SK_RootCrown.fbx','SK_RootCrown',VERSION,fbx(),u.FbxFactory())
    for a in (mesh,mesh.skeleton,mesh.physics_asset):
        if a:save(a)
    textures={}
    for role in ('BaseColor','Normal','MetallicRoughness'):
        tex=import_file(ROOT/'Textures'/('T_RootCrown_'+role+'.png'),'T_RootCrown_'+role,VERSION+'/Textures')
        tex.set_editor_property('srgb',role=='BaseColor')
        if role=='Normal':
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property('flip_green_channel',True)
        elif role=='MetallicRoughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        textures[role]=tex;save(tex)
    mat=create('M_RootCrown',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',True);mat.set_editor_property('used_with_skeletal_mesh',True)
    slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for role,pin,prop,channel in [('BaseColor','BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('Normal','Normal',u.MaterialProperty.MP_NORMAL,'RGB'),('MetallicRoughness','Roughness',u.MaterialProperty.MP_ROUGHNESS,'G'),('MetallicRoughness','Metallic',u.MaterialProperty.MP_METALLIC,'B')]:
        sample=ME.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.texture=textures[role]
        sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if role=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
        ME.connect_material_property(sample,channel,prop);ME.connect_material_expressions(sample,channel,slab,pin)
    ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(mat);save(mat)
    slots=list(mesh.materials)
    for s in slots:s.material_interface=mat
    mesh.set_editor_property('materials',slots)
    LIB.set_metadata_tag(mesh,'RootCrown.Source','User decimated SmartRig GLB; original geometry/UV/PBR; radial crown rig V01')
    save(mesh)
    clips={};report['root_units']={}
    for role in ('Idle','CrownRigDemo'):
        clip=import_file(ROOT/'Exports'/('A_RootCrown_'+role+'.fbx'),'A_RootCrown_'+role,VERSION+'/Animations',fbx(True,mesh.skeleton),u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',True)
        clip.set_preview_skeletal_mesh(mesh);report['root_units'][role]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation build did not finish')
        save(clip);clips[role]=clip
    save(mesh.skeleton)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.RootCrownRigPreview)
    bp=create('BP_RootCrownRigPreview',DEST,u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class());defaults.set_editor_property('visual_mesh',mesh)
    defaults.set_editor_property('preview_animation',clips['CrownRigDemo'])
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose_at(clips['Idle'],mesh,0.))]
    required=json.loads((ROOT/'Reports/rig.json').read_text('utf8'))['added_bones']
    missing=[n for n in required if n not in names]
    if missing:raise RuntimeError('Imported rig missing bones: '+str(missing))
    S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    report.update(stage='assets_saved',mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),blueprint=bp.get_path_name(),
        bones=names,lod_count=S.get_lod_count(mesh),lod0_vertices=S.get_num_verts(mesh,0),sections=S.get_num_sections(mesh,0),
        clips={r:dict(path=c.get_path_name(),duration=c.get_play_length()) for r,c in clips.items()},
        navigation_radius=225,navigation_height=450,display_height_cm=350,physics_asset=mesh.physics_asset.get_path_name() if mesh.physics_asset else None)
    record();print('ROOT_CROWN_ASSETS_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
