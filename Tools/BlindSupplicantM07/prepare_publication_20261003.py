"""Write the explicitly reviewed M07 archive plan and small public recovery index.

This prepares records only. archive_publication_20261003.ps1 performs the
authorized moves and per-file SHA-256 readback. It does not inspect UE packages.
"""
import hashlib
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
TOOLS = PROJECT/'Tools/BlindSupplicantM07'
OUT = ROOT/'Publication20261003'
OUT.mkdir(parents=True, exist_ok=True)
planned = {}


def add(file, reason, replacement):
    if not file.is_file():
        return
    relative = file.relative_to(PROJECT).as_posix()
    planned.setdefault(relative, {'path': relative, 'reason': reason, 'replacement': replacement})


for group in ('Authoring/AnatomyV03', 'Authoring/BeforeFragmentRepairV02',
              'Authoring/BeforeInteractingGills', 'Authoring/FragmentRepairV02',
              'RecoveryV04', 'RecoveryV05', 'MotionV03', 'MotionV04', 'Motion', 'Delivery', 'MCP'):
    for file in (ROOT/group).rglob('*'):
        add(file, 'Retired failed/superseded output or early diagnostic; no current authoring input',
            'Original source chain V06-V18, PalmArmMotionV20 and FullReferenceGaitV21 retained')

for file in ROOT.rglob('*'):
    if not file.is_file() or file.is_relative_to(OUT):
        continue
    if any(part.startswith('Before') for part in file.relative_to(ROOT).parts[:-1]):
        add(file, 'Retired before-change backup; active authoring masters retained', 'Current editable master and saved asset at original path')
    elif file.suffix in ('.blend1', '.blend2') and file.with_suffix('.blend').is_file():
        add(file, 'Blender automatic backup with retained current .blend', file.with_suffix('.blend').relative_to(PROJECT).as_posix())

retired_scripts = (
    'repair_source_v02.py', 'rebind_fragment_cloth_v02.py', 'repair_anatomy_v03.py',
    'normalize_source_v04.py', 'rebuild_complete_anatomy_v05.py',
    'assemble_source_v03.py', 'assemble_source_v04.py', 'assemble_source_v05.py',
    'export_motion_v05.py', 'import_anatomy_v03.py', 'import_anatomy_v04.py',
    'import_anatomy_v05.py', 'import_fragment_repair_v02.py', 'import_unified_frame_v02.py',
    'rollback_v03_read_frames.py', 'complete_anatomy_v03_background.ps1',
    'complete_fragment_repair_v02_background.ps1', 'complete_recovery_v04_background.ps1',
    'complete_recovery_v05_background.ps1', 'read_broken_import_frames_v04.py',
    'read_current_breakage_v05.py', 'read_donor_body_v05.py', 'read_imported_skin_v05.py',
    'read_native_skin_v05.py', 'read_source_skin_v05.py', 'read_fragment_authoring_context.py',
)
for name in retired_scripts:
    add(TOOLS/name, 'Failed V02-V05 installation or one-off diagnosis, not an imported current helper',
        'Current original-model production/import scripts and V21 locomotion importer retained')
for file in (TOOLS/'MCP').rglob('*'):
    add(file, 'Early bridge transport/diagnostic output', 'Current saved asset receipts retained locally')
for name in ('A_M07_SlowWalk.fbx', 'A_M07_Chase.fbx'):
    add(ROOT/'PalmArmMotionV20/Motion'/name, 'Superseded V20 locomotion export; shared master/manifest retained for V21',
        'FullReferenceGaitV21/Motion/'+name)

(OUT/'archive-plan.json').write_text(json.dumps({'files': list(planned.values())}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

roles = {
    'Original': 'Immutable user Meshy GLB and original source',
    'Inputs': 'Original concept and source views, local only',
    'Textures': 'Original texture/UV source, local only',
    'Audio': 'Current wall mimic audio and authoring input',
    'Authoring': 'Source extraction, anatomical records and regions; retired subdirectories indexed separately',
    'RecoveryOriginalV06': 'Frozen original model and reference definition used by subsequent source chain',
    'RecoveryOriginalV07': 'Original human hand anatomy/input; keep despite rejected dog-leg output',
    'RecoveryOriginalV08': 'Original surface/reference chain and anatomical import helpers',
    'RecoveryOriginalV09': 'Original six gill surfaces and mapped UV source',
    'LocomotionV10': 'Input to V11/V13 body and hand production chain',
    'RecoveryHandsV11': 'Hand/arm repair and immutable 83-bone reference',
    'RunningV12': 'V13 assembly input, not current run animation',
    'ArmGillCollisionV12': 'V13 assembly input, not a recommended collision budget',
    'RecoveryV13Arms': 'V13 original body assembly input',
    'RecoveryV13Legs': 'V13 original body assembly input',
    'RecoveryOriginalV13': 'Current base appearance, Physics Asset and non-locomotion actions',
    'CombatMagicV14': 'V15 death/casting editable master input',
    'MotionRecoveryV15': 'Current death, gather, release and V16/V17 motion input',
    'ArmSweepV16': 'Current arm weight source and sweep helper functions',
    'LegJointsV17': 'Current leg weights/signed knee frame; motion used by V18',
    'BodyMotionV18': 'Current display/cloth/proxy, V20 attack source and V19 locomotion input',
    'VideoLocomotionV19': 'Local video study and lawful CC0 donor; editable input to V20',
    'PalmArmMotionV20': 'Current idle/sweeps and direct V21 source, fingers and gill keys',
    'FullReferenceGaitV21': 'Current two locomotion clips and editable authoring source, not visually accepted',
}
retained = {'scope': 'Recovery dependencies retained locally, not payload redistribution',
            'content_moved': False, 'directories': [
                {'path': (ROOT/name).relative_to(PROJECT).as_posix(), 'role': role}
                for name, role in roles.items()],
            'shared_helpers': ['author_motion_v04.py', 'author_running_v12.py',
                              'repair_attack_arms_v13.py', 'author_sweep_cast_v14.py',
                              'author_cast_v15.py', 'author_locomotion_death_v15.py',
                              'author_power_sweep_v16.py', 'author_leg_joint_motion_v17.py'],
            'unchanged_content_root': 'Content/Monsters/BlindSupplicantM07',
            'content_reason': 'Native constructor fallbacks, package references and shared skeleton/material dependencies; no raw .uasset moves'}
(OUT/'retained-recovery-dependencies.json').write_text(json.dumps(retained, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

receipt = json.loads((ROOT/'FullReferenceGaitV21/ue_full_reference_gait_delivery_v21.json').read_text(encoding='utf-8-sig'))
body = json.loads((ROOT/'BodyMotionV18/ue_body_motion_delivery_v18.json').read_text(encoding='utf-8-sig'))
handoff = {
    'date': '2026-10-03', 'monster_id': 'BlindSupplicantM07',
    'current_revision': 'FullReferenceGaitV21', 'paused_by_user': True,
    'saved': receipt['saved'], 'runtime_tested': False, 'visual_accepted': False,
    'f6_blueprint': '/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.BP_BlindSupplicantM07_C',
    'mesh': receipt['mesh'], 'skeleton': receipt['skeleton'], 'physics_asset': body['physics_asset'],
    'simulation_source': body['simulation_source'], 'speed_values': receipt['speed_values'],
    'locomotion': {role: {'asset': data['asset'], 'duration_s': data['duration_s']}
                   for role, data in receipt['clips'].items()},
    'retained_action_references': receipt['retained_action_references'],
    'public_contains_binary_assets': False,
    'local_source_contract': 'Original identity/UV/bind retained; V16 arm, V17 leg, V18 bounded cloth contact, V20 idle/sweeps/lead, V15 death/casting',
    'recovery_boundary': 'Restore lawful local payloads before authoring; Git alone does not restore a complete playable installation',
}
(OUT/'runtime-handoff.json').write_text(json.dumps(handoff, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'archive_files_planned': len(planned), 'plan': str(OUT/'archive-plan.json')}, ensure_ascii=False))
