"""Produce M10 UE packages. No gameplay, previews, screenshots or acceptance tests."""
from pathlib import Path
import json,math,sys,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler';REV='M10DedicatedRig20261003V1'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
record_path=ROOT/'ue_asset_receipt.json'
report=json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def record():record_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def own(asset):LIB.set_metadata_tag(asset,'M10.Revision',REV)
def save(asset):
    own(asset)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required asset missing: '+path)
    return asset
def existing(path):
    if not LIB.does_asset_exist(path):return None
    asset=load(path)
    if LIB.get_metadata_tag(asset,'M10.Revision')!=REV:raise RuntimeError('Preserving unowned asset '+path)
    return asset
def create(name,cls,factory,folder=DEST):
    asset=existing(folder+'/'+name)
    if asset:return asset
    asset=TOOLS.create_asset(name,folder,cls,factory)
    if asset is None:raise RuntimeError('Create failed: '+name)
    own(asset);return asset
def imp(file,name,folder,options=None):
    asset=existing(folder+'/'+name)
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options
    TOOLS.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if asset is None:
        asset=next((a for p in task.imported_object_paths if isinstance((a:=u.load_asset(p)),u.AnimSequence)),None)
    if asset is None:raise RuntimeError('Import did not produce '+name)
    own(asset);return asset

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 packages')
report['stage']='importing';record()
native_available=hasattr(u,'M10Mawcrawler')
try:
    textures={}
    for semantic in ('BaseColor','MetallicRoughness','NormalGL'):
        tex=imp(ROOT/(semantic+'.png'),'T_M10_'+semantic,DEST+'/Textures')
        tex.set_editor_property('srgb',semantic=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='NormalGL' else u.TextureCompressionSettings.TC_MASKS if semantic=='MetallicRoughness' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('never_stream',False)
        if semantic=='NormalGL':tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[semantic]=tex
    matpath=DEST+'/Materials/M_M10_MeshySurface';material=existing(matpath)
    if material is None:
        material=create('M_M10_MeshySurface',u.Material,u.MaterialFactoryNew(),DEST+'/Materials')
        material.set_editor_property('used_with_skeletal_mesh',True)
        material.set_editor_property('two_sided',True)
        material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for semantic in textures:
            node=MEL.create_material_expression(material,u.MaterialExpressionTextureSample)
            node.set_editor_property('texture',textures[semantic])
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if semantic=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            links=[('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)] if semantic=='MetallicRoughness' else [('RGB',u.MaterialProperty.MP_NORMAL if semantic=='NormalGL' else u.MaterialProperty.MP_BASE_COLOR)]
            for output,prop in links:
                if not MEL.connect_material_property(node,output,prop):raise RuntimeError('Material connection failed: '+semantic)
        errors=MEL.recompile_material(material)
        if isinstance(errors,(list,tuple)) and errors:raise RuntimeError('Material compile failed: '+str(errors))
        save(material)

    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=True
        options.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        mesh=imp(ROOT/'Delivery/SK_M10_Mawcrawler.fbx','SK_M10_Mawcrawler',DEST,options)
        skeleton=mesh.get_editor_property('skeleton');own(skeleton)
        slots=list(mesh.get_editor_property('materials'))
        for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('enable_per_poly_collision',False)
        save(skeleton);save(mesh)
        physics=mesh.get_editor_property('physics_asset')
        if physics is None:raise RuntimeError('Mesh import did not create a physics package')
        if native_available and not u.M10Mawcrawler.build_physics(mesh,physics):raise RuntimeError('M10 physics production failed')
        save(physics);save(mesh)
        report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name())
        clips={};contracts=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8'))
        for role,row in contracts['clips'].items():
            op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
            data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
            clip=imp(row['file'],'A_M10_'+role,DEST+'/Animations',op)
            clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
            clip.set_preview_skeletal_mesh(mesh)
            report.setdefault('root_unit_adaptation',{})[role]=match_bind_root_scale(clip,mesh)
            save(clip);clips[role]=clip
        report['animations']={k:v.get_path_name() for k,v in clips.items()};record()
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))

    # Determine the actual FBX import forward using the bind skeleton, then
    # author the corresponding component yaw. No actor/gameplay probe needed.
    op=u.AnimPoseEvaluationOptions();op.set_editor_property('optional_skeletal_mesh',mesh)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clips['Idle'],0.,op)
    front=u.AnimPoseExtensions.get_ref_bone_pose(pose,'head',u.AnimPoseSpaces.WORLD).translation
    middle=u.AnimPoseExtensions.get_ref_bone_pose(pose,'body_center',u.AnimPoseSpaces.WORLD).translation
    yaw=-math.degrees(math.atan2(front.y-middle.y,front.x-middle.x))
    if not native_available:
        report.update(stage='mesh_material_clips_saved_native_binding_pending',mesh_yaw=yaw,native_rebuild_required=True)
        record();u.log('M10_SOURCE_ASSETS_SAVED_NATIVE_BUILD_PENDING')
        raise SystemExit(0)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.MonsterAIController.static_class())
    ai=create('BP_M10AIController',u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(ai)
    u.get_default_object(ai.generated_class()).set_editor_property('behavior',load('/Game/Monsters/AI/BT_Monster'));save(ai)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.M10Mawcrawler.static_class())
    bp=create('BP_M10Mawcrawler',u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh)
    for prop,role in [('idle_clip','Idle'),('move_clip','Walk'),('bite_clip','Bite'),('death_clip','Death')]:
        if role=='Bite' and LIB.get_metadata_tag(bp,'M10.CombatRevision'):continue
        cdo.set_editor_property(prop,clips[role])
    cdo.get_editor_property('combat').set_editor_property('hit_clip',clips['Hit'])
    cdo.set_editor_property('ai_controller_class',ai.generated_class())
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
    # A later turning pass owns its dedicated graph and four clip bindings.
    if not LIB.get_metadata_tag(bp,'M10.TurningRevision'):
        component.set_anim_instance_class(u.FatZombieAnimInstance.static_class())
    component.set_editor_property('relative_rotation',u.Rotator(pitch=0.,yaw=yaw,roll=0.))
    component.set_editor_property('relative_location',u.Vector(0.,0.,-225.))
    component.set_editor_property('override_materials',[material]);save(bp)
    if not u.PoisonMaggotMonster.compile_material_assets([material]):raise RuntimeError('M10 material compilation failed')
    save(material)
    report.update(stage='assets_saved',blueprint=bp.get_path_name(),mesh_yaw=yaw,material=material.get_path_name(),f6_id='M10Mawcrawler',f6_name='沉匣 M-10',native_rebuild_required=False)
    record();u.log('M10_ASSET_PRODUCTION_COMPLETE '+DEST)
except Exception:
    report['stage']='production_failed';report['error']=traceback.format_exc();record();raise
