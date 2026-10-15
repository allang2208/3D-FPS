"""Import heavier HeQue gait and preserve the existing attack/reaction/corpse bindings."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/WeightyMoveV02'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/WeightyMoveV02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report={'stage':'importing','saved':[],'runtime_tested':False,'multiplayer_tested':False}
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('record','save','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/heavy_import','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before changing HeQue animation bindings')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue assets')
    old=PROJECT/'Content/Monsters/HeQue/BP_HeQue.uasset';backup=ROOT/'Before/BP_HeQue.uasset'
    if old.exists() and not backup.exists():shutil.copy2(old,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('HeQue foundation assets missing')
    recipe=json.loads((ROOT/'Records/authoring.json').read_text('utf8'));clips={};report['root_units']={}
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    for item in recipe['clips']:
        options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        clip=import_file(ROOT/'Export'/(item['name']+'.fbx'),item['name'],VERSION,options,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',True);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][item['role']]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compilation unfinished: '+item['name'])
        save(clip);clips[item['role']]=clip
    save(mesh.skeleton);u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for prop,role in [('move_clip','Move'),('turn_left_clip','TurnLeft'),('turn_right_clip','TurnRight')]:cdo.set_editor_property(prop,clips[role])
    for prop,value in dict(walk_speed=recipe['walk_speed'],return_speed=recipe['return_speed'],turn_speed=recipe['turn_speed'],
        stride_distance=recipe['stride_cm'],turn_stride_degrees=recipe['turn_stride_degrees'],stopping_distance=280.,sweep_trigger_range=355.).items():cdo.set_editor_property(prop,value)
    move=cdo.get_editor_property('character_movement')
    move.set_editor_property('max_acceleration',recipe['acceleration']);move.set_editor_property('braking_deceleration_walking',recipe['braking'])
    move.set_editor_property('max_walk_speed',recipe['walk_speed'])
    LIB.set_metadata_tag(bp,'HeQue.Movement','HeavyV02: 72% stance, 198.53cm cycle travel, 100cm/s, 42deg/s, staggered body/core/chain settling')
    LIB.set_metadata_tag(bp,'HeQue.AttackEntry','Live player range/facing/sight entry, independent from per-contact collision; close pursuit avoids wide NavMesh projection stop')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='weighty_move_saved',blueprint=bp.get_path_name(),clips={role:clip.get_path_name() for role,clip in clips.items()},
        stride_cm=recipe['stride_cm'],walk_speed=recipe['walk_speed'],return_speed=recipe['return_speed'],turn_speed=recipe['turn_speed'],
        contact_damage_unchanged=True,attack_clip=cdo.get_editor_property('sweep_clip').get_path_name(),
        contact_frames=len(cdo.get_editor_property('sweep_frames')))
    record();print('HEQUE_WEIGHTY_MOVE_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
