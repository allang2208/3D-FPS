"""Apply M10-referenced movement settings to M25 without changing its authored crawl stride."""
from pathlib import Path
import json,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Monsters/VortexCofferM25'
REV='M25Movement20261004V2'
LIB=u.EditorAssetLibrary
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False,rendered=False)
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('PIE active: stop the play session before writing Blueprint defaults')
    if any(p.get_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved M25 assets')
    reference=u.load_asset('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler')
    bp=u.load_asset(BASE+'/BP_VortexCofferM25')
    if reference is None or bp is None:raise RuntimeError('M10/M25 Blueprint missing')
    ref=u.get_default_object(reference.generated_class())
    refmove=ref.get_editor_property('character_movement')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    actor=u.get_default_object(bp.generated_class())
    move=actor.get_editor_property('character_movement')
    settings=dict(walk_speed=float(ref.get_editor_property('walk_speed')),animation_walk_speed=16.)
    for key,value in settings.items():actor.set_editor_property(key,value)
    motion=dict(max_walk_speed=settings['walk_speed'],max_acceleration=float(refmove.get_editor_property('max_acceleration')),
        braking_deceleration_walking=float(refmove.get_editor_property('braking_deceleration_walking')))
    for key,value in motion.items():move.set_editor_property(key,value)
    yaw=float(refmove.get_editor_property('rotation_rate').yaw)
    move.set_editor_property('rotation_rate',u.Rotator(pitch=0.,yaw=yaw,roll=0.))
    LIB.set_metadata_tag(bp,'M25.MovementRevision',REV)
    if not LIB.save_loaded_asset(bp,False):raise RuntimeError('M25 Blueprint save failed')
    record['saved'].append(bp.get_path_name())
    record.update(stage='assets_saved',reference=reference.get_path_name(),actor_settings=settings,
        movement_settings=motion,rotation_rate_yaw_deg_s=yaw,
        animation_source_speed_cm_s=16.,animation_rate_at_full_speed=settings['walk_speed']/16.,
        animation_cycle_at_full_speed_s=2.8/(settings['walk_speed']/16.),
        animation_driver='existing M25AnimInstance: crawl phase advances from actual ground velocity / authored 16 cm/s stride',
        reference_turning_note='M10 uses a separate eight-leg movement solver; M25 retains its own movement and uses the 75 deg/s configured RotationRate',
        native_build='not required: existing Blueprint properties only; native animation driver unchanged')
    receipt();u.log('M25_MOVEMENT_V2_SAVED '+json.dumps(record))
try:main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
