"""Save M25's active search/pursuit defaults; no game or verification session."""
from pathlib import Path
import json,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Monsters/VortexCofferM25'
REV='M25Hunting20261004V1'
LIB=u.EditorAssetLibrary
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False)
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    a=u.load_asset(path)
    if a is None:raise RuntimeError('Missing asset '+path)
    return a
def save(a):
    LIB.set_metadata_tag(a,'M25.HuntingRevision',REV)
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    record['saved'].append(a.get_path_name());receipt()
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve session before asset writes')
    if any(p.get_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved M25 assets')
    ai=load(BASE+'/BP_M25AIController')
    u.BlueprintEditorLibrary.compile_blueprint(ai)
    controller=u.get_default_object(ai.generated_class())
    controller.set_editor_property('behavior',load('/Game/Monsters/AI/BT_Monster'))
    controller.set_editor_property('memory_seconds',20.)
    save(ai)
    bp=load(BASE+'/BP_VortexCofferM25')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    values=dict(walk_speed=40.,animation_walk_speed=16.,aggro_radius=3000.,leash_radius=4500.,
        stopping_distance=270.,search_for_players=True,search_radius=1200.,
        ai_controller_class=ai.generated_class(),auto_possess_ai=u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    for key,value in values.items():cdo.set_editor_property(key,value)
    movement=cdo.get_editor_property('character_movement')
    for key,value in dict(max_walk_speed=40.,max_acceleration=90.,braking_deceleration_walking=120.,
        rotation_rate=u.Rotator(pitch=0.,yaw=55.,roll=0.),orient_rotation_to_movement=True,
        run_physics_with_no_controller=True).items():
        movement.set_editor_property(key,value)
    save(bp)
    record.update(stage='assets_saved',walk_speed_cm_s=40,animation_source_speed_cm_s=16,
        search_radius_cm=1200,aggro_cm=3000,leash_cm=4500,stopping_center_distance_cm=270,
        sight='360 degrees; living visible players only; obstacles retain line-of-sight blocking',
        memory_seconds=20,navigation='existing shared BT and full-size M10 supported nav agent',
        behavior='search while idle; approach to mouth range; resume pursuit during cooldowns; face nearby target',
        attacks='existing independent physical bite and magic channels preserved')
    receipt();u.log('M25_HUNTING_BLUEPRINTS_SAVED')
try:main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
