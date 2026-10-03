"""Record actual asset saving and necessary native build completion."""
import argparse
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV13'
parser = argparse.ArgumentParser()
parser.add_argument('--editor-log', required=True)
parser.add_argument('--game-log', required=True)
args = parser.parse_args()
receipt_path = OUT/'ue_delivery_v13.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
if not receipt.get('saved'):
    raise RuntimeError('V13 model, actions and AI/F6 must actually save first.')
build = {'native_editor_and_game_built': True, 'native_editor_build_log': args.editor_log,
         'native_game_build_log': args.game_log, 'runtime_tested': False,
         'visual_tested': False, 'tested': False, 'user_review_pending': True}
receipt.update(build)
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/filename
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(build)
    record.update({'native_original_recovery_defaults_compiled': True,
                   'ue_save_receipt': str(receipt_path), 'body_physics_receipt': str(receipt_path),
                   'interacting_gills_receipt': str(receipt_path),
                   'animation_revision_retained': 'OriginalV13 full twelve-clip composition with V11 reference',
                   'locomotion_revision': 'RunningV13 minimal leg roll, retained 160/360cm/s stride',
                   'locomotion_source': str(OUT/'motion_manifest_v13.json'),
                   'arm_gill_collision_manifest': str(OUT/'cloth_ue_manifest_original_v13.json'),
                   'active_model_source': str(OUT/'M07_Original_Recovery_V13.blend'),
                   'cloth_distance_cm': {'resume': 1000., 'suspend': 1400.},
                   'generated_lods': receipt['generated_lods']})
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
source = OUT/'source_delivery_v13.json'
record = json.loads(source.read_text(encoding='utf-8'))
record.update({'ue_imported': True, 'ue_save_receipt': str(receipt_path), **build})
source.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V13_ACTUAL_SAVE_AND_NATIVE_BUILD_RECORDS_SAVED', flush=True)
