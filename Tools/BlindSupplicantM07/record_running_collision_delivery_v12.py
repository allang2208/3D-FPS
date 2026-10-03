"""Record completed native builds after actual V12 asset saving."""
import argparse
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RunningCollisionV12'
parser = argparse.ArgumentParser()
parser.add_argument('--editor-log', required=True)
parser.add_argument('--game-log', required=True)
args = parser.parse_args()
path = OUT/'ue_running_collision_delivery_v12.json'
receipt = json.loads(path.read_text(encoding='utf-8-sig'))
if not receipt.get('saved'):
    raise RuntimeError('V12 assets and AI/F6 references have not actually saved.')
receipt.update({'native_editor_and_game_built': True, 'native_editor_build_log': args.editor_log,
                'native_game_build_log': args.game_log, 'runtime_tested': False,
                'visual_tested': False, 'tested': False, 'user_review_pending': True})
path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
collision_source = ROOT/'ArmGillCollisionV12/arm_gill_collision_delivery_v12.json'
collision_record = json.loads(collision_source.read_text(encoding='utf-8-sig'))
collision_record.update({'ue_imported': True, 'ue_save_receipt': str(path),
                         'runtime_tested': False, 'tested': False, 'user_review_pending': True})
collision_source.write_text(json.dumps(collision_record, ensure_ascii=False, indent=2), encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    target = ROOT/filename
    record = json.loads(target.read_text(encoding='utf-8-sig'))
    record.update({'native_running_collision_defaults_compiled': True,
                   'native_running_collision_editor_build_log': args.editor_log,
                   'native_running_collision_game_build_log': args.game_log,
                   'animation_stage': 'Ten V11 non-locomotion actions retained; V12 larger SlowWalk/Chase clips and matched speeds saved',
                   'animation_revision_retained': 'OriginalV11 non-locomotion actions and corrected reference',
                   'motion_authoring_receipt': str(ROOT/'RunningV12/motion_manifest_v12.json'),
                   'body_physics_receipt': str(path), 'interacting_gills_receipt': str(path),
                   'active_animation_source': str(ROOT/'RunningV12/M07_Original_Running_V12.blend'),
                   'active_cloth_collision_source': str(ROOT/'ArmGillCollisionV12/cloth_ue_manifest_original_v12.json'),
                   'runtime_tested': False, 'visual_tested': False,
                   'tested': False, 'user_review_pending': True})
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V12_ACTUAL_SAVE_AND_NATIVE_BUILD_RECORDS_UPDATED', flush=True)
