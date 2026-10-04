"""Prepare the reviewed M07 V38 archive and public recovery index; no UE calls."""
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
TOOLS = PROJECT/'Tools/BlindSupplicantM07'
OUT = ROOT/'Publication20261004'
OUT.mkdir(parents=True, exist_ok=True)
planned = {}

def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def add(file, reason, replacement):
    if file.is_file():
        relative = file.relative_to(PROJECT).as_posix()
        planned.setdefault(relative, dict(path=relative, reason=reason, replacement=replacement))

retired = {
    'FullReferenceGaitV21': 'HeavyGaitV22 -> InwardArmSwingV23 -> ClearanceSweepV25 movement',
    'FlowCastV24': 'LibraryCastV28 -> SupportHoverV30 casting',
    'ReferenceChainSweepV26': 'LibrarySweepV27 -> SupportHoverV30 -> IdleLegSupportV32 melee',
    'MembraneStabilityV31': 'MembraneSkinV35 -> WitchClothV36 -> ShoulderClothV38',
    'CoherentMembraneV34': 'Active Witch-style Chaos in ShoulderClothV38',
}
for directory, replacement in retired.items():
    for file in (ROOT/directory).rglob('*'):
        add(file, 'Rejected or superseded standalone production; no active authoring input', replacement)

# V33's one-time package rollback is retired together with its V31 snapshot.
# Its foot-support samples and native transition implementation remain active.
retired_tools = (
    'author_full_reference_gait_v21.py', 'import_full_reference_gait_v21.py',
    'author_flow_cast_v24.py', 'import_flow_cast_v24.py',
    'author_reference_chain_sweep_v26.py', 'import_reference_chain_sweep_v26.py',
    'author_membrane_stability_v31.py', 'import_membrane_stability_v31.py',
    'diagnose_membrane_source_v31.py', 'inspect_membrane_v31.py', 'read_membrane_config_v31.py',
    'import_coherent_membrane_v34.py', 'restore_membrane_v33.ps1', 'save_recover_membrane_v33.py',
    'prepare_publication_20261003.py',
)
for name in retired_tools:
    add(TOOLS/name, 'Retired production/rollback or completed one-time publication recipe',
        'Current retained source chain and Publication20261004 recovery index')

for file in ROOT.rglob('*'):
    if not file.is_file() or file.is_relative_to(OUT):
        continue
    if any(part.startswith('Before') for part in file.relative_to(ROOT).parts[:-1]):
        add(file, 'Previous revision snapshot; recoverable in trash, not a current source input',
            'Current editable masters, saved packages and archive SHA-256 manifest')
    elif file.suffix in ('.blend1', '.blend2') and file.with_suffix('.blend').is_file():
        add(file, 'Automatic Blender backup; current editable master retained',
            file.with_suffix('.blend').relative_to(PROJECT).as_posix())

write('archive-plan.json', {'files': list(planned.values())})
roles = {
    'HeavyGaitV22': 'Original accepted leg/body timing; direct V23 source and shared helpers',
    'InwardArmSwingV23': 'Direct V25 source; palm orientation and opposite-step swing',
    'ClearanceSweepV25': 'Current movement and clearance profile; mixed master also contains retired sweeps',
    'LibrarySweepV27': 'Current melee foundation, native Attack_D and accepted first-second fitting parameters',
    'LibraryCastV28': 'Native SnappySpell_Vexa retarget and direct V30 casting input',
    'DirectionalDeathV29': 'Current eight directional death clips and editable source',
    'SupportHoverV30': 'Current floating cast and direct V32 source; mixed master includes superseded leg solution',
    'IdleLegSupportV32': 'Current melee with idle-calibrated leg support',
    'RecoverMembraneV33': 'Retain transition foot samples/diagnosis; old package restoration tools retired',
    'MembraneSkinV35': 'Current lower-membrane weights and direct V36/V38 topology/rig inputs',
    'WitchClothV36': 'Direct V38 continuous-proxy source; old shoulder eligibility is superseded',
    'BodyClothMaterialV37': 'Saved Clothing material usage fix and recovery recipe',
    'ShoulderClothV38': 'Current editable display/proxy, shoulder capture, saved delivery and distance LODs',
    'MeleeSpeed20261003': 'Current palm-to-claw damage capsule, 63/129 movement and source-speed contract',
}
write('retained-recovery-dependencies.json', {
    'scope': 'M07 V38 publication; local payloads are not redistributed',
    'legacy_index': 'Publication20261003/retained-recovery-dependencies.json',
    'legacy_override': 'FullReferenceGaitV21 is now retired; older V06-V20 source dependencies remain',
    'directories': [{'path': (ROOT/name).relative_to(PROJECT).as_posix(), 'role': role}
                    for name, role in roles.items()],
    'explicit_required_file': 'LibrarySweepV27/RecoveryFix/accepted_motion_manifest_v27.json',
    'mixed_masters_retained': ['ClearanceSweepV25', 'SupportHoverV30'],
    'content_moved': False,
    'content_reason': 'Keep native fallbacks and package dependencies; do not move uassets outside UE package management',
})
receipt = json.loads((ROOT/'ShoulderClothV38/ue_shoulder_cloth_delivery_v38.json').read_text(encoding='utf-8-sig'))
write('runtime-handoff.json', {
    'date': '2026-10-04', 'monster_id': 'BlindSupplicantM07', 'membrane_revision': 'ShoulderClothV38',
    'saved': receipt['saved'], 'runtime_tested': False, 'visual_accepted': False,
    'blueprint': '/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07',
    'mesh': '/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18',
    'proxy': '/Game/Monsters/BlindSupplicantM07/Working/SK_M07_ClothProxyV38',
    'clips': receipt['retained_clips'], 'settings': receipt['retained_settings'],
    'physical_vertices': receipt['cloth']['physical_vertices'],
    'pinned_vertices': receipt['cloth']['pinned_vertices'], 'lods': receipt['generated_lods'],
    'cloth_resume_distance_cm': 1200, 'cloth_suspend_distance_cm': 1600,
    'public_binary_assets': False,
    'save_and_exit': 'All packages saved; subsequent PythonScriptPlugin shutdown exception, exit code 3',
    'recovery_boundary': 'Restore lawful local source/asset dependencies; Git alone is not a playable content backup',
})
print(json.dumps({'archive_files_planned': len(planned), 'plan': str(OUT/'archive-plan.json')}))
