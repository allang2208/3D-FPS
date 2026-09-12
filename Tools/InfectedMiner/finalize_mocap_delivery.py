"""Package the existing CMU delivery and recorded evidence; does not run tests."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / 'SourceAssets/InfectedMiner20260912'
SAVED = ROOT / 'Saved/InfectedMiner'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


attack = read(ASSET / 'Delivery/attack-authoring.json')
rig = read(ASSET / 'Delivery/rigging.json')
rig['body_vertices_before_accepted_forearm_replacement'] = 14241
rig['body_vertices'] = 12237
rig['forearm_hand_vertices_each'] = 8353
rig['initial_body_transfer_maximum_influences'] = rig.pop('maximum_influences', 4)
rig['initial_transfer_statistics_scope'] = 'Original generated body only; excludes mature forearm/hand replacement.'
rig['weight_source'] = 'Generated body: mature reference skin transfer. Accepted forearm through hand: original Manny continuous skin and bind.'
rig['accepted_hand_snapshot'] = 'Review/Hand_UserAccepted_20260912'
rig.pop('custom_attack', None)
rig['attack_source'] = attack['version']
rig['actions']['Attack'] = {k: attack[k] for k in ['seconds', 'frames', 'contact_time', 'contact_end', 'minimum_surface_z_m']}
rig['actions']['Attack'].update(sample_rate=30, samples=67, custom_attack_ik=False)
write(ASSET / 'Delivery/rigging.json', rig)

sources = read(ASSET / 'Reference/CMU/sources.json')
sources.pop('official_subject', None)
sources.update(date='2026-09-12', selected_clip='02_07.bvh', source_fps=120,
    official_clip_index='https://mocap.cs.cmu.edu/search.php?subjectnumber=2',
    revision_pin='Downloaded file SHA-256; repository commit unavailable.',
    use_terms='CMU permits research and commercial use. Bruce Hahne adds no restrictions to the BVH conversion. See READMEFIRST.txt; not a CC0 declaration.',
    credit='CMU Graphics Lab Motion Capture Database, funded by NSF EIA-0196217; BVH conversion by Bruce Hahne.')
write(ASSET / 'Reference/CMU/sources.json', sources)

build = (SAVED / 'build-cmu-final.log').read_text(errors='replace')
village_log = (SAVED / 'cmu-village-pass.log').read_text(errors='replace')
report = {
    'date': '2026-09-12', 'version': attack['version'],
    'evidence_policy': 'Previously completed evidence only. No additional isolated-map run after reading the new user-testing rule.',
    'artistic_user_acceptance': 'Pending user review; hand/grasp accepted before motion replacement.',
    'build': {'success': 'Result: Succeeded' in build, 'log': 'Saved/InfectedMiner/build-cmu-final.log'},
    'import': read(SAVED / 'mocap-import.json'),
    'hand_lock': read(ASSET / 'Previews/FBX_CMU/accepted-hand-validation.json'),
    'fbx': read(ASSET / 'Previews/FBX_CMU/fbx-validation.json'),
    'roundtrip': read(ASSET / 'Previews/FBX_CMU/attack-pose-roundtrip.json'),
    'ue_mesh_color_export': read(ASSET / 'Previews/FBX/ue-mesh-export-validation.json'),
    'village': read(SAVED / 'cmu-village-pass.json'),
    'isolated': {'run_for_current_motion': False},
}
report['village']['log'] = 'Saved/InfectedMiner/cmu-village-pass.log'
report['village']['surface_measurements'] = re.findall(r'MINER_SURFACE .*', village_log)
report['village']['limb_measurements'] = re.findall(r'MINER_PHYSICS_LENGTH .*', village_log)
write(ROOT / 'Docs/InfectedMiner20260912.validation.json', report)

paths = [p for p in (ASSET / 'Delivery').iterdir() if p.suffix.lower() in ['.blend', '.fbx', '.png', '.json']]
paths += [ASSET / 'Previews' / n for n in ['InfectedMiner_Attack.gif', 'InfectedMiner_Attack.mp4', 'InfectedMiner_CMU_Attack.gif', 'InfectedMiner_CMU_Attack.mp4']]
paths += list((ASSET / 'Previews/FBX_CMU').glob('*.json'))
paths += [ASSET / 'Previews/FBX/ue-mesh-export-validation.json']
files = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]
write(ASSET / 'delivery_manifest.json', {
    'character': 'InfectedMiner', 'date': '2026-09-12', 'host': 'UE 5.8.2',
    'generation': {'provider': 'TokenHub', 'model': 'hy-3d-3.1', 'job_id': '1490283299431399424', 'submissions': 1, 'cache': 'Saved/Hunyuan3D/Candidates/infected-miner-male-v01-20260912'},
    'sources': [
        {'asset': '/Game/ZombieFemale/Asset/Meshes/ZombieFemale_NurseOutfit', 'role': 'Local humanoid hierarchy and base animations', 'redistribution': 'Binary publication not cleared'},
        {'asset': 'SourceAssets/MannyGraspDonor20260912', 'role': 'Accepted mature forearm/hand skin and VRE grouped grasp', 'redistribution': 'Local only; original source licenses apply'},
        {'asset': 'Authored pickaxe', 'role': 'Original rigid wood/iron tool geometry'},
        {'asset': sources['repository'], 'clip': '02_07.bvh', 'sha256': next(f['sha256'] for f in sources['files'] if f['file'] == '02_07.bvh'), 'role': 'Human optical capture, mirrored retarget with source timing', 'terms': sources['use_terms']}
    ],
    'body_topology': 'Generated head, torso and legs; mature continuous forearms and hands',
    'accepted_hand_snapshot': 'Review/Hand_UserAccepted_20260912',
    'active_mesh': report['import']['mesh_preserved'], 'active_attack': report['import']['clip'],
    'attack_contract': attack, 'attack_range_cm': 150,
    'artistic_user_acceptance': report['artistic_user_acceptance'], 'files': files,
})
print('MINER_CMU_DELIVERY_PACKAGED', len(files))
