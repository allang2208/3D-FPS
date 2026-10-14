"""Save motion assets, then bind the native locomotion stage to its existing F6 BP."""
import ast, json, traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/MotionV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report={'stage':'importing_motion','saved':[],'runtime_tested':False}
RECEIPT=ROOT/'Reports/ue-locomotion-import.json'
# Reuse the exact FBX unit conversion of the already delivered rig, without
# executing the earlier material/mesh/demo import again.
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
helpers=ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','import_file','fbx','pose_at','align_root_units')],type_ignores=[])
exec(compile(helpers,'RootCrown/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; motion import remains queued')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Root Crown has unsaved target packages')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    mesh=u.load_asset(DEST+'/RigV01/SK_RootCrown');clips={}
    for role in ('Idle','Move','TurnLeft','TurnRight'):
        name='A_RootCrown_'+role+'_V01'
        opts=fbx(True,mesh.skeleton);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        clip=import_file(ROOT/'Exports/MotionV01'/(name+'.fbx'),name,VERSION,opts,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',True)
        clip.set_preview_skeletal_mesh(mesh);align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression did not complete')
        save(clip);clips[role]=clip
    save(mesh.skeleton)
    # Assets remain saved even when a loaded editor still has the old native
    # class. The same script can bind them after the native build is loaded.
    anim_class=u.load_class(None,'/Script/FPSGAME.RootCrownAnimInstance')
    if not anim_class:
        report['stage']='motion_saved_native_reload_pending';record()
    else:
        bp=u.load_asset(DEST+'/BP_RootCrownRigPreview')
        u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
        cdo.set_editor_property('visual_mesh',mesh)
        for prop,role in [('idle_clip','Idle'),('move_clip','Move'),('turn_left_clip','TurnLeft'),('turn_right_clip','TurnRight')]:cdo.set_editor_property(prop,clips[role])
        for prop,value in [('walk_speed',150.),('turn_speed',150.),('stride_distance',90.),('turn_stride_degrees',72.),('aggro_radius',2200.),('leash_radius',3200.)]:cdo.set_editor_property(prop,value)
        cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
        cdo.set_editor_property('ai_controller_class',u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C'))
        cdo.set_editor_property('use_controller_rotation_yaw',False)
        # Tick capability is configured by the new native constructor;
        # FTickFunction::bCanEverTick is not exposed through editor Python.
        move=cdo.get_editor_property('character_movement')
        if 'RootCrownMovementComponent' not in move.get_class().get_name():raise RuntimeError('Native movement subobject still needs an editor reload')
        for prop,value in [('max_walk_speed',150.),('rotation_rate',u.Rotator(pitch=0.,yaw=150.,roll=0.)),
                           ('max_acceleration',360.),('braking_deceleration_walking',600.),
                           ('orient_rotation_to_movement',True),('use_controller_desired_rotation',False),('can_walk_off_ledges',False)]:move.set_editor_property(prop,value)
        mesh_component=cdo.get_editor_property('mesh');mesh_component.set_anim_instance_class(anim_class)
        cdo.set_editor_property('tags',[u.Name('Enemy'),u.Name('RootCrown')])
        u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
        report.update(stage='motion_and_blueprint_saved',blueprint=bp.get_path_name(),walk_speed=150,turn_speed=150,wander_speed=75,stride_distance=90,turn_stride_degrees=72)
        record()
    print('ROOT_CROWN_MOTION_IMPORT '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
