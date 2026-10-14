"""Save Root Crown's reaction clips and bind the native health/control/death path."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/ReactionsV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report={'stage':'importing_reactions','saved':[],'gameplay_tested':False,'multiplayer_tested':False}
RECEIPT=ROOT/'Reports/ue-reactions-import.json'
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'RootCrown/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before asset integration')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Root Crown assets')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    body=u.load_asset(DEST+'/RigV01/SK_RootCrown');clips={}
    for item in json.loads((ROOT/'Reports/reactions_authoring.json').read_text('utf8'))['clips']:
        opts=fbx(True,body.skeleton);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        clip=import_file(ROOT/'Exports/ReactionsV01'/(item['name']+'.fbx'),item['name'],VERSION,opts,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',item['loop'])
        clip.set_preview_skeletal_mesh(body);align_root_units(clip,body)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression did not finish: '+item['name'])
        save(clip);clips[item['role']]=clip
    save(body.skeleton)
    sounds={}
    for role in ('Hit','Land','Death'):
        sound=import_file(ROOT/'Audio/ReactionsV01'/('RootCrown_'+role+'.wav'),'S_RootCrown_'+role,VERSION+'/Audio')
        save(sound);sounds[role]=sound
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    defaults.set_editor_property('hit_clips',[clips[r] for r in ('HitFront','HitRight','HitBack','HitLeft')])
    for key,role in [('stun_clip','Stun'),('air_clip','Air'),('land_clip','Land'),('get_up_clip','GetUp'),('death_clip','Death')]:defaults.set_editor_property(key,clips[role])
    for key,role in [('hit_sound','Hit'),('land_sound','Land'),('death_sound','Death')]:defaults.set_editor_property(key,sounds[role])
    # Current health is initialized from MaxHealth by BeginPlay, not an editable asset default.
    for key,value in [('max_health',3000.),('level',12),('rank',u.MonsterRank.BOSS),('experience_reward',480),('corpse_seconds',25.)]:defaults.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='reactions_saved',blueprint=bp.get_path_name(),clips={r:c.get_path_name() for r,c in clips.items()},health=3000,rank='Boss',level=12,corpse_seconds=25,ground_death_handoff_seconds=.65,
                  preserved_slash_clip=defaults.get_editor_property('slash_clip').get_path_name(),preserved_needle_clip=defaults.get_editor_property('needle_clip').get_path_name(),preserved_root_clip=defaults.get_editor_property('root_clip').get_path_name(),preserved_body_material=defaults.get_editor_property('slash_material').get_path_name())
    record();print('ROOT_CROWN_REACTIONS_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
