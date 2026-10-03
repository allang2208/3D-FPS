"""Save the requested +50% movement pace on the existing M07 AI/F6 Blueprint."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'MeleeSpeed20261003'
REPORT=OUT/'ue_melee_speed_delivery.json'
BP='/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07'
LIB=u.EditorAssetLibrary

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 pace belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('M07_PACE_PIE_PRESERVED')
    if any(p.get_path_name()==BP for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 Blueprint edits preserved.')

source=json.loads((OUT/'melee_source.json').read_text(encoding='utf-8'))
bp=u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
speeds={p:source['settings'][p]*1.5 for p in ('walk_speed','chase_speed')}
for prop,value in speeds.items():
    current=defaults.get_editor_property(prop)
    if min(abs(current-source['settings'][prop]),abs(current-value))>.001:
        raise RuntimeError('M07 movement setting changed since intake: '+prop)
backup=OUT/'Before/BP_BlindSupplicantM07.uasset'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.uasset',backup)
report=dict(saved=False,blueprint=BP,assets=[],movement_multiplier=1.5,speeds=speeds,
    source_speeds={p:defaults.get_editor_property(p) for p in ('source_walk_speed','source_chase_speed')},
    retained_combat={p:defaults.get_editor_property(p) for p in ('attack_damage','attack_range',
        'left_contact_time','right_contact_time','contact_window_seconds','melee_playback_rate')},
    retained_clips={p:defaults.get_editor_property(p).get_path_name() for p in ('slow_walk_clip','chase_clip',
        'melee_left_clip','melee_right_clip','magic_gather_clip','magic_release_clip')},
    melee_contact='Palm-to-claw capsule, existing arc and reach, one commitment per attack',
    runtime_tested=False,rendered=False,user_review_pending=True)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for prop,value in speeds.items():defaults.set_editor_property(prop,value)
# Keep authored source speeds unchanged: velocity/source speed now evaluates
# both existing locomotion clips at 1.5x, without a second rate multiplier.
defaults.get_editor_property('character_movement').set_editor_property('max_walk_speed',speeds['chase_speed'])
LIB.set_metadata_tag(bp,'MeleeSpeedRevision','20261003: palm-claw contact and movement pace x1.5')
if not LIB.save_loaded_asset(bp,False):raise RuntimeError('M07 pace Blueprint save failed')
report.update(saved=True,assets=[bp.get_path_name()],stage='Original AI/F6 Blueprint saved; native build recorded separately')
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/name
    record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(melee_contact_revision='PalmClawCapsule20261003',movement_speed_revision='Pace150Percent20261003',
        movement_speeds_cm_s=speeds,melee_speed_delivery=str(REPORT),runtime_tested=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_MELEE_SPEED_SAVED '+str(REPORT))
