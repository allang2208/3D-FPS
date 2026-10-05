"""Background import/save of M08's authored rig, PBR, actions and playable BP.
Does not load a level, spawn actors, render, or run gameplay tests.
"""
import json, traceback, runpy
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/ProductionV01_20261004'
DEST='/Game/Monsters/LurkerM08'
REV='M08_BackV02_FittedRigV01_20261004'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'state':'authoring_ue_assets','revision':REV,'saved':[], 'animations':{},
        'runtime_tested':False,'rendered':False,'decimated':False,'native_class':'/Script/FPSGAME.LurkerM08Monster'}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    a=u.load_asset(path)
    if a is None:raise RuntimeError('Missing asset '+path)
    return a
def save(a):
    LIB.set_metadata_tag(a,'M08.Revision',REV)
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in REPORT['saved']:REPORT['saved'].append(a.get_path_name())
    record()
def existing(path):
    if not LIB.does_asset_exist(path):return None
    a=load(path)
    if LIB.get_metadata_tag(a,'M08.Revision') != REV:
        raise RuntimeError('Preserving independent asset '+path)
    return a
def create(name,folder,cls,factory):
    a=existing(folder+'/'+name)
    if a:return a,False
    a=TOOLS.create_asset(name,folder,cls,factory)
    if a is None:raise RuntimeError('Creation failed '+name)
    LIB.set_metadata_tag(a,'M08.Revision',REV)
    return a,True
def task(file,name,folder,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder
    t.automated=True;t.save=False;t.replace_existing=False
    if options:t.options=options
    TOOLS.import_asset_tasks([t]);return t

def match_root_units(clip,mesh):
    # Required FBX import conversion, not a playback test: Blender's Armature
    # container is stripped by animation-only import, leaving its 100x scale.
    opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE
    opt.optional_skeletal_mesh=mesh
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opt)
    ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,'root',u.AnimPoseSpaces.LOCAL)
    current=u.AnimPoseExtensions.get_bone_pose(pose,'root',u.AnimPoseSpaces.LOCAL)
    expected=[ref.scale3d.x,ref.scale3d.y,ref.scale3d.z]
    before=[current.scale3d.x,current.scale3d.y,current.scale3d.z]
    factors=[a/b for a,b in zip(expected,before)]
    if max(abs(v-1.) for v in factors)<1e-5:return {'before':before,'bind':expected,'changed':False}
    if max(abs(v-100.) for v in factors)>.01:raise RuntimeError('Unexpected FBX root units '+str(factors))
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    pos=[];rot=[];scl=[]
    for i in range(count):
        p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),opt)
        root=u.AnimPoseExtensions.get_bone_pose(p,'root',u.AnimPoseSpaces.LOCAL)
        pos.append(root.translation);rot.append(root.rotation);scl.append(u.Vector(*expected))
    control=clip.get_editor_property('controller');control.open_bracket('M08 FBX root unit conversion',False)
    try:
        if not control.set_bone_track_keys('root',pos,rot,scl,False):raise RuntimeError('Root key conversion failed')
    finally:control.close_bracket(False)
    return {'before':before,'bind':expected,'changed':True}

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if not hasattr(u,'LurkerM08Monster'):raise RuntimeError('Build the M08 native class before importing')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(DEST):raise RuntimeError('Preserving unsaved M08 package '+package.get_name())
    materials=[]
    texture_files=[{'BaseColor':'slot0_Image_0.png','MetallicRoughness':'slot0_Image_1.png','Normal':'slot0_Image_2.png'},
                   {'BaseColor':'slot1_M08_ArchInterior_BaseColor.png','MetallicRoughness':'slot1_M08_ArchInterior_MetallicRoughness.png'}]
    for slot,maps in enumerate(texture_files):
        textures={}
        for semantic,file in maps.items():
            name='T_M08_%s_%s'%('Skin' if slot==0 else 'InnerArch',semantic)
            tex=existing(DEST+'/Textures/'+name)
            if tex is None:
                task(ROOT/'Textures'/file,name,DEST+'/Textures');tex=load(DEST+'/Textures/'+name)
                tex.set_editor_property('srgb',semantic=='BaseColor')
                tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal'
                    else u.TextureCompressionSettings.TC_DEFAULT if semantic=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
                tex.set_editor_property('never_stream',False)
                if semantic=='Normal':tex.set_editor_property('flip_green_channel',True)
                save(tex)
            textures[semantic]=tex
        name='M_M08_'+('Skin' if slot==0 else 'InnerArch')
        mat,new=create(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        if new:
            mat.set_editor_property('used_with_skeletal_mesh',True)
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
            substrate=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
            substrate.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
            samples={}
            for semantic,tex in textures.items():
                node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
                node.set_editor_property('parameter_name',semantic);node.set_editor_property('texture',tex)
                node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic=='Normal'
                    else u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
                samples[semantic]=node
            wires=[('BaseColor','RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),
                   ('MetallicRoughness','G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
                   ('MetallicRoughness','B',u.MaterialProperty.MP_METALLIC,'Metallic')]
            if 'Normal' in samples:wires.append(('Normal','RGB',u.MaterialProperty.MP_NORMAL,'Normal'))
            for semantic,out,prop,pin in wires:
                if not MEL.connect_material_property(samples[semantic],out,prop):raise RuntimeError('Material output '+pin)
                if not MEL.connect_material_expressions(samples[semantic],out,substrate,pin):raise RuntimeError('Substrate pin '+pin)
            if not MEL.connect_material_property(substrate,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
            MEL.layout_material_expressions(mat);MEL.recompile_material(mat);save(mat)
        materials.append(mat)
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        mesh=existing(DEST+'/SK_LurkerM08')
        if mesh is None:
            op=u.FbxImportUI();op.automated_import_should_detect_type=False
            op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
            op.import_as_skeletal=True;op.import_mesh=True;op.import_animations=False
            op.import_materials=False;op.import_textures=False;op.create_physics_asset=True
            data=op.skeletal_mesh_import_data
            data.set_editor_property('update_skeleton_reference_pose',False)
            data.set_editor_property('use_t0_as_ref_pose',False)
            data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
            task(ROOT/'SK_LurkerM08.fbx','SK_LurkerM08',DEST,op);mesh=load(DEST+'/SK_LurkerM08')
        skeleton=mesh.get_editor_property('skeleton')
        slots=list(mesh.get_editor_property('materials'))
        for i,entry in enumerate(slots):entry.material_interface=materials[i];slots[i]=entry
        mesh.set_editor_property('materials',slots)
        subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        settings=subsystem.get_lod_build_settings(mesh,0)
        settings.set_editor_property('recompute_normals',False)
        settings.set_editor_property('recompute_tangents',True)
        settings.set_editor_property('use_mikk_t_space',True)
        settings.set_editor_property('use_full_precision_u_vs',True)
        subsystem.set_lod_build_settings(mesh,0,settings)
        physics=mesh.get_editor_property('physics_asset')
        if physics is None:raise RuntimeError('M08 physics asset was not created')
        count=u.LurkerM08Monster.author_lurker_physics(mesh)
        if count<=0:raise RuntimeError('M08 anatomical physics authoring failed')
        REPORT.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),physics_bodies=count)
        save(physics);save(skeleton);save(mesh)
        for role,row in SOURCE['clips'].items():
            name='A_M08_'+role;clip=existing(DEST+'/Animations/'+name)
            if clip is None:
                op=u.FbxImportUI();op.automated_import_should_detect_type=False
                op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
                op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
                op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
                ad=op.anim_sequence_import_data
                ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',60)
                ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
                ad.set_editor_property('remove_redundant_keys',False)
                t=task(row['file'],name,DEST+'/Animations',op)
                clip=next((a for a in [u.load_asset(p) for p in t.imported_object_paths] if isinstance(a,u.AnimSequence)),None)
                if clip is None:raise RuntimeError('Animation import failed '+role)
                clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
                clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
                clip.set_editor_property('rate_scale',1.)
                clip.set_preview_skeletal_mesh(mesh)
                REPORT.setdefault('root_units',{})[role]=match_root_units(clip,mesh)
                save(clip)
            REPORT['animations'][role]=clip.get_path_name();record()
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.QuadrupedAnimationSet.static_class())
    dataset,_=create('DA_M08_AnimationSet',DEST,u.QuadrupedAnimationSet,factory)
    actions={}
    for role,row in SOURCE['clips'].items():
        action=u.QuadrupedTemplateAction()
        for k,value in {'sequence':load(REPORT['animations'][role]),'loop':row['loop'],
                        'hold_last_pose':not row['loop'],'terminal':role=='Death','play_rate':1.,
                        'blend_seconds':.08 if role.startswith(('Attack','Hit')) else .16,
                        'contact_start_seconds':row['contact'][0],'contact_end_seconds':row['contact'][1]}.items():
            action.set_editor_property(k,value)
        actions[role]=action
    dataset.set_editor_property('actions',actions);dataset.set_editor_property('reference_mesh',mesh)
    dataset.set_editor_property('walk_speed',100.);dataset.set_editor_property('run_speed',210.)
    dataset.set_editor_property('run_blend_start_ratio',.60);dataset.set_editor_property('run_blend_full_ratio',.88)
    save(dataset)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.LurkerM08Monster.static_class())
    bp,_=create('BP_LurkerM08',DEST,u.Blueprint,factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('animation_set',dataset)
    controller=u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C')
    if controller is None:raise RuntimeError('Shared Behavior Tree controller missing')
    cdo.set_editor_property('ai_controller_class',controller)
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
    rotation=u.Rotator();rotation.yaw=-90.
    component.set_editor_property('relative_rotation',rotation)
    component.set_editor_property('relative_location',u.Vector(0,0,-70.))
    save(bp)
    REPORT.update(state='assets_saved_and_playable_blueprint_bound',blueprint=bp.get_path_name(),
                  animation_set=dataset.get_path_name(),f6_id='LurkerM08',f6_name='伏窥者 M-08',
                  behavior='low pursuit and close pounce bite',nav_profile='PoisonMaggot R70 H140 Step40',
                  contact_windows_source_seconds={'AttackBite':[.30,.42],'AttackPounce':[.52,.64]})
    record()
    # A full mesh/action reinstall must also restore the M08 traversal slot and
    # defaults, rather than silently dropping the later surface-movement feature.
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_traversal.py'),run_name='__m08_traversal_install__')
    # Restore the current anatomical revision after a full baseline reinstall.
    # Older mesh/actions remain retained as production inputs and rollback assets.
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_canine_v03.py'),run_name='__m08_canine_v03_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_bonehead_v04.py'),run_name='__m08_bonehead_v04_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_pounce_v05.py'),run_name='__m08_pounce_v05_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_air_cannon_v06.py'),run_name='__m08_air_cannon_v06_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_rim_speed_v07.py'),run_name='__m08_rim_speed_v07_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_motion_v09.py'),run_name='__m08_motion_v09_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_death_v10.py'),run_name='__m08_death_v10_install__')
    runpy.run_path(str(PROJECT/'Tools/LurkerM08/install_air_warning_v11.py'),run_name='__m08_air_warning_v11_install__')
    u.log('M08_ASSETS_SAVED '+bp.get_path_name())

try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
