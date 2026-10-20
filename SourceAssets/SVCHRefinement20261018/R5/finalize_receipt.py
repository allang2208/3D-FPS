"""Record the completed R5 build/run after reviewing its actual captured frames."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[2]
label, build_name = sys.argv[1:3]
run = P / 'Saved/SVCHPoseAudit' / label

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    return path.relative_to(P).as_posix()

build = O / build_name
assert 'Result: Succeeded' in build.read_text(encoding='utf-8', errors='replace')
saved = read(O / 'saved_assets.json')
result = read(run / 'result.json')
summary = read(run / 'summary.json')
installed = read(O / 'install_receipt.json')
profile = read(O / 'profile_receipt_r5.json')
model = read(O / 'model_receipt_r5.json')
assert saved['passed'] and all(c['passed'] for c in saved['checks'])
assert result['completed'] and result['process_exit'] == 0
assert not summary['missing_images']
assert summary['meshes'] == [installed['mesh']]
assert summary['profiles'] == [installed['profile']]
assert (O / 'r4-r5-comparison.jpg').exists()

validation = {
    'revision': 'R5',
    'recorded_at': datetime.now().astimezone().isoformat(),
    'authorization': 'User requested wrist crease repair, smoother mechanisms, and self-check.',
    'build_log': relative(build),
    'build_result': 'Succeeded',
    'saved_asset_checks': len(saved['checks']),
    'saved_asset_checks_passed': saved['passed'],
    'saved_asset_report': relative(O / 'saved_assets.json'),
    'runtime_directory': relative(run),
    'runtime_result': result,
    'telemetry_rows': sum(summary['stages'].values()),
    'captured_images': len(list((run / 'Frames').glob('*.png'))),
    'runtime_stages': summary['stages'],
    'observed_meshes': summary['meshes'],
    'observed_profiles': summary['profiles'],
    'profile_authoring': profile,
    'triangles': {'weapon': model['triangles'] - 37086, 'arms': 37086, 'total': model['triangles']},
    'comparison_image': relative(O / 'r4-r5-comparison.jpg'),
    'comparison_frames': read(O / 'comparison_frames.json'),
    'visual_review': {
        'basis': 'Actual offscreen game captures; same scene and inspection phase as R4.',
        'right_wrist': 'The deep twisted pinch at the peak inspection roll is removed; wrist-to-forearm transition is continuous.',
        'mechanisms': 'Rear aperture, front protective arc, pins and muzzle have rounded silhouettes; sight alignment retained.',
        'return': 'Inspection returns to base two-hand hold.'
    },
    'unverified': ['audio', 'multiplayer', 'third-person', 'all optional gunsmith configurations'],
    'build_unblock': {'file': 'Source/FPSGAME/UI/ColdSteelConsumablePresentation.h', 'change': 'FJsonObject forward declaration struct -> class to match UE JsonObject.h; no UI logic change.'}
}
(O / 'validation_receipt.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
previous = read(O.parent / 'delivery_receipt.json')
mesh = P / 'Content/Weapons/SVCH/Refined20261018/R5/SK_SVCH_Refined_R5.uasset'
delivery = {
    'target': 'FPSGAMEEditor Win64 Development',
    'status': 'R5 built, saved and checked in offscreen game; wrist twist and rounded mechanisms reviewed',
    'revision': 'R5',
    'mesh': installed['mesh'],
    'profile': installed['profile'],
    'assets_saved': installed['saved'],
    'saved_asset_checks': len(saved['checks']),
    'saved_asset_checks_passed': saved['passed'],
    'runtime_tested': True,
    'validation_receipt': relative(O / 'validation_receipt.json'),
    'build_log': relative(build),
    'binary_sha256': digest(P / 'Binaries/Win64/UnrealEditor-FPSGAME.dll'),
    'mesh_sha256': digest(mesh),
    'fbx_sha256': installed['fbx_sha256'],
    'profile_source_sha256': installed['profile_sha256'],
    'native_arm_correctives_saved': 18,
    'previous_delivery': previous
}
(O.parent / 'delivery_receipt.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: validation[k] for k in ('build_result', 'saved_asset_checks', 'telemetry_rows', 'captured_images')}, indent=2))
