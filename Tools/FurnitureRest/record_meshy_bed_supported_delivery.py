"""Summarize the saved joint/support review and the actual scoped publication."""
import json
from pathlib import Path
import numpy as np
OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/MeshyBedSupportedHands20261024'
BASE=OUT.parent/'MeshyBedSideHands20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
old,new=read(BASE/'authored.json'),read(OUT/'authored.json');pelvis=new['names'].index('pelvis')
others=[i for i in range(len(new['names'])) if i!=pelvis]
for role,take in new['clips'].items():
    a,b=np.asarray(old['clips'][role]['frames']),np.asarray(take['frames'])
    if not np.array_equal(a[:,others,:3],b[:,others,:3]) or not np.array_equal(a[...,7:],b[...,7:]):raise RuntimeError('Bone lengths/scales changed: '+role)
    if not np.array_equal(a[:,pelvis,:2],b[:,pelvis,:2]):raise RuntimeError('Horizontal root timing changed.')
    if role.endswith('.Idle') and not np.array_equal(a,b):raise RuntimeError('Idle changed.')
result={
    'source_revision':str(BASE),'saved_assets':read(OUT/'assets_saved.json'),
    'publication':read(OUT/'publication.json'),
    'authoring_bone_lengths_scales_horizontal_root_and_idle_preserved':True,
    'changed_motion':'seated support height, brief foot-frame clearance, relaxed wrists, distributed torso recline, planted palms and release; exit mirrors enter',
    'native_joint_and_contact_review':read(OUT/'native_ergonomics_review.json'),
    'stage_joins':read(OUT/'native_stage_review.json'),
    'geometry':read(OUT/'geometry_audit_saved.json'),
    'hand_body':read(OUT/'hand_body_contact_saved.json'),
    'skin_support':read(OUT/'support_contacts_saved.json'),
    'review_scope':'Jason native body/head and two Queen bed meshes; both native skeletons and hand support tracks. Kaitlin skinned contacts and clothing combinations not reviewed.',
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),
    'full_cycle_preview':str(OUT/'ReviewSaved/bed_full_cycle.gif'),
    'game_tested':False,'interactive_editor_started':False,'multiplayer_tested':False,
    'git_commit':None,'git_push':None,
}
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('MESHY_BED_SUPPORTED_DELIVERY_RECORDED')
