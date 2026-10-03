"""Save the pre-V31 membrane settings without reverting V32 action refs."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'RecoverMembraneV33'
REPORT=OUT/'ue_recover_membrane_delivery_v33.json'
BP='/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07'
MESH='/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 restoration belongs to FPSGAME.')
restore=json.loads((OUT/'membrane_package_restore_v33.json').read_text(encoding='utf-8-sig'))
if not restore['restored']:raise RuntimeError('Restore the pre-V31 mesh package before saving its actor.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('V33 restored packages are saved in the requested offline window.')
backup=OUT/'Before/BP_BlindSupplicantM07.uasset'
if not backup.exists():shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.uasset',backup)
bp=u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
previous=json.loads((ROOT/'MembraneStabilityV31/ue_membrane_delivery_v31.json').read_text(encoding='utf-8'))
defaults.set_editor_property('gill_clearance_angle_degrees',previous['previous_clearance_degrees'])
u.EditorAssetLibrary.set_metadata_tag(bp,'MembraneRevision','PreV31RestoredV33: exact original mesh package and 18 degree clearance')
u.EditorAssetLibrary.set_metadata_tag(bp,'RecoveryTransitionRevision','FootSupportBlendV33: grounded local-pose crossfade')
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('V33 Blueprint save failed.')
report=dict(revision='RecoverMembraneV33',saved=True,mesh_restored=MESH,blueprint_saved=bp.get_path_name(),
    package_restore_receipt=str(OUT/'membrane_package_restore_v33.json'),
    gill_clearance_degrees=defaults.get_editor_property('gill_clearance_angle_degrees'),
    retained_references={p:defaults.get_editor_property(p).get_path_name() for p in (
        'visual_mesh','idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip',
        'magic_gather_clip','magic_release_clip','death_clip')},
    recovery_fix='M07-only local-pose crossfade support from 4 foot bones; no traces or runtime IK',
    membrane_status='Exact pre-V31 restored; continuous panel redesign documented, not applied',
    runtime_tested=False,rendered=False,user_review_pending=True)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
restore['blueprint_clearance_restore_pending']=False
(OUT/'membrane_package_restore_v33.json').write_text(json.dumps(restore,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/filename
    record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(membrane_revision='PreV31RestoredV33',membrane_delivery=str(REPORT),
        membrane_proxy_asset='/Game/Monsters/BlindSupplicantM07/Working/SK_M07_ClothBuildSource_BodyMotionV18',
        recovery_transition_revision='FootSupportBlendV33',recovery_transition_delivery=str(REPORT),
        runtime_tested=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V33_RECOVERY_MEMBRANE_SAVED '+str(REPORT))
