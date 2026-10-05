"""Import/save only M08's two V05 leap actions and their shared time contract."""
import ast, json, shutil, traceback, hashlib
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/PounceV05_20261004'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/PounceV05';REV='M08_PounceV05_20261004'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'animations':{},'runtime_tested':False,'rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    value=u.load_asset(path)
    if value is None:raise RuntimeError('Missing asset '+path)
    return value
def save(asset):
    LIB.set_metadata_tag(asset,'M08.PounceRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in REPORT['saved']:REPORT['saved'].append(asset.get_path_name())
    record()
module=ast.parse((PROJECT/'Tools/LurkerM08/install_lurker.py').read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='match_root_units')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<M08 root unit adapter>','exec'),globals())
def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    anim_class=u.load_class(None,'/Script/FPSGAME.LurkerM08AnimInstance')
    if anim_class is None:raise RuntimeError('M08 native animation class missing')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    skeleton=mesh.get_editor_property('skeleton')
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for name in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({'mesh':dataset.reference_mesh.get_path_name(),
        'actions':{str(k):v.sequence.get_path_name() if v.sequence else None for k,v in dataset.actions.items()}},ensure_ascii=False,indent=2),encoding='utf-8')
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        for role,row in SOURCE['clips'].items():
            name='A_M08_'+role+'_PounceV05';path=DEST+'/Animations/'+name
            clip=u.load_asset(path) if LIB.does_asset_exist(path) else None
            if clip and LIB.get_metadata_tag(clip,'M08.PounceRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
            digest=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
            if clip is None or LIB.get_metadata_tag(clip,'M08.SourceFBXHash')!=digest:
                op=u.FbxImportUI();op.automated_import_should_detect_type=False
                op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
                op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
                op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
                ad=op.anim_sequence_import_data
                ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
                ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
                ad.set_editor_property('remove_redundant_keys',False)
                task=u.AssetImportTask();task.filename=row['file'];task.destination_name=name;task.destination_path=DEST+'/Animations'
                task.automated=True;task.save=False;task.replace_existing=clip is not None;task.options=op
                if clip:task.replace_existing_settings=True
                TOOLS.import_asset_tasks([task])
                clip=next((load(p) for p in task.imported_object_paths if isinstance(load(p),u.AnimSequence)),None)
                if clip is None:raise RuntimeError('Animation import did not return '+role)
                clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
                clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
                clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
                REPORT.setdefault('root_units',{})[role]=match_root_units(clip,mesh)
                LIB.set_metadata_tag(clip,'M08.SourceFBXHash',digest);save(clip)
            REPORT['animations'][role]=clip.get_path_name();record()
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    actions=dict(dataset.get_editor_property('actions'))
    for role,row in SOURCE['clips'].items():
        entry=actions.get(role,u.QuadrupedTemplateAction())
        for key,value in {'sequence':load(REPORT['animations'][role]),'loop':False,'hold_last_pose':True,
            'terminal':False,'play_rate':1.,'blend_seconds':.08,
            'contact_start_seconds':row['contact'][0],'contact_end_seconds':row['contact'][1]}.items():entry.set_editor_property(key,value)
        actions[role]=entry
    dataset.set_editor_property('actions',actions);save(dataset)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('animation_set',dataset)
    for key,value in {'pounce_windup':.06,'pounce_recovery':.16,'pounce_travel_start':.24,'pounce_travel_end':.74}.items():cdo.set_editor_property(key,value)
    cdo.get_editor_property('mesh').set_anim_instance_class(anim_class);save(bp)
    REPORT.update(state='pounce_v05_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
        mesh=mesh.get_path_name(),anim_class=anim_class.get_path_name(),f6_id='LurkerM08',
        preserved_actions=[str(k) for k in actions if str(k) not in SOURCE['clips']],
        timing={'source_takeoff':.24,'source_landing':.74,'pounce_contact':[.70,.88],
            'flight_seconds':'clamp(distance_cm/760 + 0.16, 0.44, 0.95)','jump_flight_max':1.05},
        authoring_source=str(ROOT/'M08_Pounce_Animated_V05.blend'))
    record();u.log('M08_POUNCE_V05_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
