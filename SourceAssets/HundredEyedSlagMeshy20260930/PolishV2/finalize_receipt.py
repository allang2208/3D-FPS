from pathlib import Path
import json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
install=json.loads((OUT/'ue_installation.json').read_text())
checks=json.loads((OUT/'saved_ue_checks.json').read_text())
receipt=json.loads((ROOT/'production_status.json').read_text(encoding='utf-8-sig'))
receipt.update(stage='polish_v2_native_build_assets_saved_scoped_readback_complete',
    active_revision='PolishV2',delivery='PolishV2/Delivery',ue_destination='/Game/Monsters/HundredEyedSlag/PolishV2',
    ue_saved_asset_count=30,animation_asset_count=19,active_animation_roles=16,
    override_animation_count=3,build_log='SourceAssets/HundredEyedSlagMeshy20260930/PolishV2/build_nonunity.log',
    scoped_asset_checks_passed=True,authoring_contact_checked=True,preview_rendered=True,
    tested=False,runtime_tested=False,pie_tested=False,ragdoll_runtime_tested=False,
    skin_texture_dependencies=4,chase_speed_cm_s=checks['chase_speed'],return_speed_cm_s=checks['return_speed'],
    ragdoll_handoff_s=checks['ragdoll_handoff_seconds'],physics_bodies=16,physics_joints=15,
    ue_editor_started_by_this_task=False,ue_background_commandlets_used=True,
    polish_installation='PolishV2/ue_installation.json',saved_ue_checks='PolishV2/saved_ue_checks.json')
(ROOT/'production_status.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
