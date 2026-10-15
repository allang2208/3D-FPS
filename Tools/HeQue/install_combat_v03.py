"""Install whole-body jump motion and requested HeQue combat settings."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/CombatV03'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/CombatV03'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report=dict(stage='importing',saved=[],gameplay_tested=False,visual_tested=False,multiplayer_tested=False)
RECEIPT=ROOT/'Records/ue-import.json'
tree=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
names=('record','save','import_file','fbx','pose_at','align_root_units')
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/combat_v03_import','exec'))

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue packages')
    for relative in ('BP_HeQue.uasset','RigV01/SK_HeQue_Skeleton.uasset'):
        source=PROJECT/'Content/Monsters/HeQue'/relative;backup=ROOT/'Before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        if source.exists() and not backup.exists():shutil.copy2(source,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('Delivered HeQue rig or Blueprint missing')
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    clips={};report['root_units']={}
    for entry in authored['clips']:
        options=fbx(True,mesh.skeleton)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',authored['fps'])
        clip=import_file(ROOT/'Export'/(entry['name']+'.fbx'),entry['name'],VERSION+'/Animations',options,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][entry['role']]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Jump animation compilation unfinished: '+entry['name'])
        save(clip);clips[entry['role']]=clip
    save(mesh.skeleton)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    report['previous']={key:float(cdo.get_editor_property(key)) for key in ('jump_height','sweep_push_distance','psychic_cooldown')}
    bindings=dict(jump_air_clip=clips['Air'],jump_dive_clip=clips['Dive'],jump_recover_clip=clips['Recover'],
        jump_height=authored['jump_height_cm'],sweep_push_distance=authored['kick_push_cm'],psychic_cooldown=authored['psychic_cooldown'])
    for key,value in bindings.items():cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.CombatV03','210cm jump; whole-body dive; accepted jump hit: cripple 5s; kick push 10m with swept wall stop; clamp stun 2s; close move rotation; ranged spell priority; psychic cooldown 30s')
    LIB.set_metadata_tag(bp,'HeQue.Weakpoint','HQ_CoreSwing suspended heart; shared weapon and direct-magic weakpoint critical path')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='combat_v03_saved',blueprint=bp.get_path_name(),
        clips={role:dict(path=clip.get_path_name(),duration=clip.get_play_length()) for role,clip in clips.items()},
        jump_height_cm=float(cdo.get_editor_property('jump_height')),kick_push_cm=float(cdo.get_editor_property('sweep_push_distance')),
        psychic_cooldown=float(cdo.get_editor_property('psychic_cooldown')),cripple_seconds=5,clamp_stun_seconds=2,
        weakpoint_bone=authored['weakpoint_bone'],charge_seconds=1.95,recovery_seconds=2.6,close_band_cm=600,
        charge_clip_preserved=cdo.get_editor_property('jump_charge_clip').get_path_name(),
        wave_material_preserved=cdo.get_editor_property('jump_wave_material').get_path_name(),f6_id='HeQue')
    record();print('HEQUE_COMBAT_V03_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
