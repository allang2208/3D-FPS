"""Record actual V11 saved assets and required native build artifacts."""
import argparse
import json
from pathlib import Path

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'RecoveryHandsV11'
parser=argparse.ArgumentParser()
parser.add_argument('--editor-log',required=True)
parser.add_argument('--game-log',required=True)
parser.add_argument('--import-log',required=True)
args=parser.parse_args()
receipt_path=OUT/'ue_hand_arm_delivery_v11.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
if not receipt.get('saved'):raise RuntimeError('V11 assets and AI/F6 references have not actually saved.')
source=json.loads((OUT/'hand_arm_delivery_v11.json').read_text(encoding='utf-8'))
source.update({'ue_imported':True,'ue_save_receipt':str(receipt_path)})
(OUT/'hand_arm_delivery_v11.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/filename
    record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({'revision':'OriginalV11HandsAndArms','geometry_revision':'OriginalV11',
        'mesh':receipt['mesh'],'skeleton':receipt['skeleton'],
        'native_hands_arms_defaults_compiled':True,
        'native_hands_arms_editor_build_log':args.editor_log,
        'native_hands_arms_game_build_log':args.game_log,
        'hands_arms_import_log':args.import_log,
        'reference_revision':'OriginalV11 corrected upperarm axes; unchanged joint positions and 83 bone names/parents',
        'skin_weights_stage':'OriginalV11 continuous shoulder/elbow/wrist/palm and soft surface-geodesic digit weights; V09 gill and V08 leg weights retained',
        'source_faces_preserved':False,
        'source_face_cleanup':'Only two secondary pinky offshoots removed and locally capped; surviving source UV retained; immutable original GLB preserved',
        'original_source_immutable_preserved':True,
        'original_primary_anatomy_preserved':True,
        'requested_arm_source_diagnosis':str(OUT/'diagnosis/authored_hand_arm_findings_v11.json'),
        'animation_stage':'Twelve matching OriginalV11 actions saved; continuous elbow planes, transported bounded wrists, V10 stride timings retained',
        'current_display_asset_requires_repair':False,
        'user_accepted_model':False,'user_accepted_motion':False,'user_review_pending':True,
        'tested':False,'runtime_tested':False,'visual_tested':False,'ue_editor_opened':False})
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
receipt.update({'native_editor_and_game_built':True,'native_editor_build_log':args.editor_log,
    'native_game_build_log':args.game_log,'production_import_log':args.import_log,
    'requested_source_diagnosis':str(OUT/'diagnosis/authored_hand_arm_findings_v11.json')})
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('M07_V11_ACTUAL_SAVE_AND_NATIVE_BUILD_RECORDS_UPDATED',flush=True)
