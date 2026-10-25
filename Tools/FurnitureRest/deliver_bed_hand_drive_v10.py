"""Final saved-animation and visual-review receipt for V10."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedHandDriveV10'
verification=json.loads((OUT/'verification.json').read_text())
media=['ReviewSaved/bed_before_after.gif','ReviewSaved/bed_hand_drive_detail.gif','ReviewSaved/bed_and_bunk.gif','ReviewSaved/apartment_and_hospital.gif','ReviewSaved/six_bed_types.jpg','ReviewSaved/bed_transition_sheet.jpg']
assert all((OUT/p).exists() for p in media)
with (OUT/'authored.json').open('rb') as stream:source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
receipt={'revision':'BedHandDriveV10','source_sha256':source_hash,'verification':verification,
    'save_commandlet_exit_code':int((OUT/'save-exit.txt').read_text().strip()),'readback_commandlet_exit_code':int((OUT/'readback-exit.txt').read_text().strip()),
    'saved_assets':json.loads((OUT/'assets_saved.json').read_text()),
    'sofa_reference':'HangingEntryV6/Rest.Sofa.Enter, first 1.15 seconds and knee hinge planes',
    'native_cpp_changed':False,'gameplay_or_network_tested':False,'interactive_editor_started':False,
    'git_committed_or_pushed':False,'media':media,
    'visual_review':'saved six-type entry/idle/exit sheet inspected; native skin, neutral material, no hair',
    'previous_version':'BedSupportedV9 scoots rejected by user for stiff body translation'}
assert receipt['save_commandlet_exit_code']==receipt['readback_commandlet_exit_code']==0
(OUT/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('BED_HAND_DRIVE_DELIVERED',len(receipt['saved_assets']))
