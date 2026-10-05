"""Save only M08's ground-constrained death animation and its formal reference."""
import ast, json, shutil, traceback, hashlib
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/DeathV10_20261005'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/DeathV10/Animations';REV='M08_DeathV10_20261005'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'runtime_tested':False,'rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    value=u.load_asset(path)
    if value is None:raise RuntimeError('Missing asset '+path)
    return value
def save(asset):
    LIB.set_metadata_tag(asset,'M08.DeathRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in REPORT['saved']:REPORT['saved'].append(asset.get_path_name())
    record()
module=ast.parse((PROJECT/'Tools/LurkerM08/install_lurker.py').read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='match_root_units')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<M08 root unit adapter>','exec'),globals())

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Gameplay is active; M08 death import has not started')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    actions={str(k):v for k,v in dataset.get_editor_property('actions').items()}
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    name='DA_M08_AnimationSet.uasset'
    if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({'actions':{k:v.sequence.get_path_name() if v.sequence else None for k,v in actions.items()}},indent=2),encoding='utf-8')
    row=SOURCE['clips']['Death'];name='A_M08_Death_DeathV10';path=DEST+'/'+name
    clip=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if clip and LIB.get_metadata_tag(clip,'M08.DeathRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
    digest=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
    if clip is None or LIB.get_metadata_tag(clip,'M08.SourceFBXHash')!=digest:
        cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
        u.SystemLibrary.execute_console_command(None,cvar+' 0')
        try:
            op=u.FbxImportUI();op.automated_import_should_detect_type=False
            op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
            op.import_materials=False;op.import_textures=False;op.skeleton=mesh.get_editor_property('skeleton')
            ad=op.anim_sequence_import_data
            ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
            ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            ad.set_editor_property('remove_redundant_keys',False)
            task=u.AssetImportTask();task.filename=row['file'];task.destination_name=name;task.destination_path=DEST
            task.automated=True;task.save=False;task.replace_existing=clip is not None;task.options=op
            if clip:task.replace_existing_settings=True
            TOOLS.import_asset_tasks([task])
            clip=next((load(p) for p in task.imported_object_paths if isinstance(load(p),u.AnimSequence)),None)
            if clip is None:raise RuntimeError('Animation import did not return Death')
            clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
            clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
            clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
            REPORT['root_units']=match_root_units(clip,mesh)
            LIB.set_metadata_tag(clip,'M08.SourceFBXHash',digest);save(clip)
        finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    entry=actions['Death']
    for key,value in {'sequence':clip,'loop':False,'hold_last_pose':True,'terminal':True,'play_rate':1.,
        'blend_seconds':.12,'contact_start_seconds':-1.,'contact_end_seconds':-1.}.items():entry.set_editor_property(key,value)
    actions['Death']=entry;dataset.set_editor_property('actions',actions);save(dataset)
    REPORT.update(state='death_v10_saved_and_bound',animation=clip.get_path_name(),animation_set=dataset.get_path_name(),
        source_duration_seconds=1.4,existing_handoff_fraction=.55,native_build_required=False,
        preserved_actions={k:v.sequence.get_path_name() if v.sequence else None for k,v in actions.items() if k!='Death'},f6_id='LurkerM08')
    record();u.log('M08_DEATH_V10_SAVED '+clip.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
