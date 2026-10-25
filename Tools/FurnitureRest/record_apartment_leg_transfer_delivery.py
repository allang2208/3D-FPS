"""Keep the native-save, local integration and offline preview evidence together."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentLegTransfer20261024R2'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
result={
    'revision':OUT.name,
    'reference':read(OUT/'References/reference.json'),
    'entry_duration_seconds':6.7,'exit_duration_seconds':7.0,
    'changes':['continuous pelvic turn instead of two rapid lateral impulses','staggered knee flexion with curved foot clearance','supported torso descent without repeated upright preparation'],
    'saved_assets':read(OUT/'assets_saved.json'),
    'saved_lengths':read(OUT/'save_complete.json')['saved_durations'],
    'publication':read(OUT/'publication.json'),
    'native_stages':read(OUT/'native_stage_review.json'),
    'native_legs':read(OUT/'native_leg_review.json'),
    'geometry':read(OUT/'geometry_audit_saved.json'),
    'hand_body_contact':read(OUT/'hand_body_contact_saved.json'),
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),
    'full_cycle_preview':str(OUT/'ReviewSaved/bed_full_cycle.gif'),
    'review_scope':'Native joint tracks for Jason and Kaitlin; compressed Jason skin against all three apartment bed models; offline preview. Female skin and clothing combinations not reviewed.',
    'game_tested':False,'interactive_editor_started':False,'multiplayer_tested':False,
    'git_commit':None,'git_push':None,
}
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('APARTMENT_LEG_TRANSFER_DELIVERED',OUT/'delivery.json')
