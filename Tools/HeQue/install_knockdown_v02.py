"""Import only the living knockdown/recovery clips and bind the original F6 actor."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/KnockdownV02'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/KnockdownV02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report=dict(stage='importing',saved=[],gameplay_tested=False,rendered=False,multiplayer_tested=False)
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('record','save','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/recovery_import','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue assets')
    for relative in ('BP_HeQue.uasset','RigV01/SK_HeQue_Skeleton.uasset'):
        source=PROJECT/'Content/Monsters/HeQue'/relative;backup=ROOT/'Before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        if source.exists() and not backup.exists():shutil.copy2(source,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('Original HeQue runtime assets missing')
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    clips={};report['root_units']={}
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    for source in authored['clips']:
        options=fbx(True,mesh.skeleton)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',authored['fps'])
        clip=import_file(ROOT/'Export'/(source['name']+'.fbx'),source['name'],VERSION,options,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][source['role']]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compilation pending: '+source['name'])
        save(clip);clips[source['role']]=clip
    save(mesh.skeleton)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    report['previous_clips']={key:cdo.get_editor_property(key).get_path_name() if cdo.get_editor_property(key) else None
        for key in ('air_clip','land_clip','get_up_clip')}
    for key,role in (('air_clip','Air'),('land_clip','Land'),('get_up_clip','GetUp')):cdo.set_editor_property(key,clips[role])
    LIB.set_metadata_tag(bp,'HeQue.Knockdown','V02: velocity-phased airborne recoil; 0.95s folded landing; grounded dwell; 3.0s alternating support and two-stage rise')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='knockdown_recovery_v02_saved',blueprint=bp.get_path_name(),f6_id='HeQue',
        clips={role:dict(path=clip.get_path_name(),duration=clip.get_play_length()) for role,clip in clips.items()},
        minimum_down_dwell=authored['minimum_down_dwell'],death_binding='Preserved SoftCorpseV02 on original living mesh')
    record();print('HEQUE_KNOCKDOWN_RECOVERY_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
