"""Save the accepted M25 bite at 2x speed with a 25 cm reach increase. No runtime tests."""
from pathlib import Path
import json, traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Monsters/VortexCofferM25'
REV='M25Bite20261004V2'
LIB=u.EditorAssetLibrary
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False,rendered=False)
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve session before asset writes')
    if any(p.get_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved M25 packages')
    bp=u.load_asset(BASE+'/BP_VortexCofferM25')
    if bp is None:raise RuntimeError('M25 Blueprint missing')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    bite=cdo.get_editor_property('bite')
    if bite is None:raise RuntimeError('M25 bite component missing')
    settings=dict(playback_rate=2.,trigger_reach=110.,contact_radius=80.)
    for key,value in settings.items():bite.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'M25.BiteTuningRevision',REV)
    if not LIB.save_loaded_asset(bp,False):raise RuntimeError('M25 Blueprint save failed')
    record['saved'].append(bp.get_path_name())
    record.update(stage='assets_saved',settings=settings,
        animation='/Game/Monsters/VortexCofferM25/Animations/A_M25_Bite_V01',
        source_duration_s=1.4,playback_duration_s=.7,source_contact_window_s=[.60,.76],
        playback_contact_window_s=[.30,.38],playback_blend_in_s=.07,playback_blend_out_s=.09,
        reach_increase_cm=25,contact_radius_increase_cm=25,
        physical_damage_and_cooldown='unchanged',magic_channel='independent and unchanged',
        collision='front cone and wall blocking retained; swept mouth contact handles frames crossing the faster contact window')
    receipt();u.log('M25_BITE_V2_BLUEPRINT_SAVED')
try:main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
