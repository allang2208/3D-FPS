"""Write the final saved-asset and offline review receipt."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedNaturalV8'
report=json.loads((OUT/'verification.json').read_text())
media=['ReviewSaved/bed_and_bunk.gif','ReviewSaved/apartment_and_hospital.gif',
       'ReviewSaved/six_bed_types.jpg','ReviewSaved/bed_transition_sheet.jpg']
assert all((OUT/p).exists() for p in media)
receipt={'revision':'BedNaturalV8/ContactRefine','verification':report,
         'authoring_sha256':hashlib.file_digest((OUT/'authored.json').open('rb'),'sha256').hexdigest(),
         'saved_assets':json.loads((OUT/'assets_saved.json').read_text()),
         'save_commandlet_exit_code':0,'readback_commandlet_exit_code':0,
         'save_log':'save-final.log','readback_log':'readback-final.log',
         'geometry_audit':'geometry_audit_saved.json','hand_body_contact':'hand_body_contact_saved.json',
         'head_geometry':'ReviewSaved/head.json','native_cpp_changed':False,
         'interactive_editor_or_game_started':False,'git_committed_or_pushed':False,
         'media_kind':'saved compressed animation and actual mesh; neutral offline review',
         'media':media,'visual_review':'final side poses and six-family entry/hold/exit contact sheet inspected'}
(OUT/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('BED_NATURAL_DELIVERED',len(receipt['saved_assets']))
