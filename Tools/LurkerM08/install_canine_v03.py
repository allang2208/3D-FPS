"""Save M08's canine-fitted revision and bind its existing gameplay entry.
New mesh/skeleton/actions are versioned. Existing traversal/combat settings stay.
"""
import ast, json, shutil, traceback, hashlib
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/CanineRigV03_20261004'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/CanineV03';REV='M08_CanineRigV03_20261004'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'animations':{},'runtime_tested':False,'rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    a=u.load_asset(path)
    if a is None:raise RuntimeError('Missing asset '+path)
    return a
def save(a):
    LIB.set_metadata_tag(a,'M08.CanineRigRevision',REV)
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in REPORT['saved']:REPORT['saved'].append(a.get_path_name())
    record()
def ours(path):
    if not LIB.does_asset_exist(path):return None
    a=load(path)
    if LIB.get_metadata_tag(a,'M08.CanineRigRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
    return a
def task(file,name,folder,options,replace=False):
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder
    t.automated=True;t.save=False;t.replace_existing=replace;t.options=options
    if replace:t.replace_existing_settings=True
    TOOLS.import_asset_tasks([t]);return t
# Reuse only the established import unit adapter, never execute the old installer.
module=ast.parse((PROJECT/'Tools/LurkerM08/install_lurker.py').read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='match_root_units')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<M08 root unit adapter>','exec'),globals())

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet')
    cdo=u.get_default_object(bp.generated_class())
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for relative in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        f=PROJECT/'Content/Monsters/LurkerM08'/relative
        if not (backup/relative).exists():shutil.copy2(f,backup/relative)
    before=ROOT/'before_references.json'
    if not before.exists():
        before.write_text(json.dumps({'mesh':dataset.reference_mesh.get_path_name(),
          'actions':{str(k):v.sequence.get_path_name() if v.sequence else None for k,v in dataset.actions.items()},
          'blueprint':bp.get_path_name()},ensure_ascii=False,indent=2),encoding='utf-8')
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        mesh=ours(DEST+'/SK_LurkerM08_CanineV03')
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
            task(SOURCE['mesh'],'SK_LurkerM08_CanineV03',DEST,op);mesh=load(DEST+'/SK_LurkerM08_CanineV03')
        skeleton=mesh.get_editor_property('skeleton')
        materials=[load(BASE+'/Materials/M_M08_Skin'),load(BASE+'/Materials/M_M08_InnerArch')]
        slots=list(mesh.get_editor_property('materials'))
        for i,entry in enumerate(slots):entry.material_interface=materials[i];slots[i]=entry
        mesh.set_editor_property('materials',slots)
        sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        settings=sub.get_lod_build_settings(mesh,0)
        settings.set_editor_property('recompute_normals',False);settings.set_editor_property('recompute_tangents',True)
        settings.set_editor_property('use_mikk_t_space',True);settings.set_editor_property('use_full_precision_u_vs',True)
        sub.set_lod_build_settings(mesh,0,settings)
        count=u.LurkerM08Monster.author_lurker_physics(mesh)
        if count<=0:raise RuntimeError('Could not author M08 physical body')
        physics=mesh.get_editor_property('physics_asset')
        save(physics);save(skeleton);save(mesh)
        REPORT.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),physics_bodies=count,
                      source_bones=len(SOURCE['bones']))
        for role,row in SOURCE['clips'].items():
            name='A_M08_'+role+'_CanineV03';clip=ours(DEST+'/Animations/'+name)
            source_hash=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
            if clip is None or LIB.get_metadata_tag(clip,'M08.SourceFBXHash')!=source_hash:
                replacing=clip is not None
                op=u.FbxImportUI();op.automated_import_should_detect_type=False
                op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
                op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
                op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
                ad=op.anim_sequence_import_data
                ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
                ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
                ad.set_editor_property('remove_redundant_keys',False)
                result=task(row['file'],name,DEST+'/Animations',op,replace=replacing)
                clip=next((load(p) for p in result.imported_object_paths if isinstance(load(p),u.AnimSequence)),None)
                if clip is None:raise RuntimeError('No animation '+role)
                clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
                clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
                clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
                REPORT.setdefault('root_units',{})[role]=match_root_units(clip,mesh)
                LIB.set_metadata_tag(clip,'M08.SourceFBXHash',source_hash)
                save(clip)
            REPORT['animations'][role]=clip.get_path_name();record()
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    # Change formal references only after every replacement action has saved.
    actions=dict(dataset.get_editor_property('actions'))
    for role,row in SOURCE['clips'].items():
        action=actions.get(role,u.QuadrupedTemplateAction())
        for key,value in {'sequence':load(REPORT['animations'][role]),'loop':row['loop'],
             'hold_last_pose':not row['loop'],'terminal':role=='Death','play_rate':1.,
             'blend_seconds':.10 if role.startswith(('Attack','Hit')) else .16,
             'contact_start_seconds':row['contact'][0],'contact_end_seconds':row['contact'][1]}.items():
            action.set_editor_property(key,value)
        actions[role]=action
    # Existing aliases must use the new skeleton too, if present.
    for alias,role in [('RunTurnLeft','Run'),('RunTurnRight','Run'),('WalkTurnLeft','Walk'),('WalkTurnRight','Walk')]:
        if alias in actions:
            action=actions[alias];action.sequence=load(REPORT['animations'][role]);actions[alias]=action
    dataset.set_editor_property('actions',actions);dataset.set_editor_property('reference_mesh',mesh)
    dataset.set_editor_property('walk_speed',100.);dataset.set_editor_property('run_speed',210.)
    save(dataset)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('animation_set',dataset)
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
    save(bp)
    REPORT.update(state='canine_rig_actions_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
       traversal_preserved=True,contact_windows_preserved=True,f6_id='LurkerM08',native_source_changed=False)
    record();u.log('M08_CANINE_V03_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
