"""Record the supplied source and the completed, scoped ordinary-bed integration."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBed20261024'
SRC=OUT.parent/'MeshySitLieBed37120261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(OUT/'assets_saved.json');publication=read(OUT/'publication.json')
if not publication['runtime_published']:raise RuntimeError('Publication is incomplete.')
inventory=read(SRC/'glb_inventory.json');request=read(SRC/'source_request.json')
request.update({
    'status':'saved_and_routed_ordinary_bed',
    'source_file':inventory['file'],'source_sha256':inventory['sha256'],
    'source_motion_reviewed':True,'retargeted':True,'runtime_routes_changed':True,
    'selected_exported_clip':'sleep','selected_source_duration_seconds':5.7,
    'saved_ue_assets':[p for routes in [saved['default'],*saved['variants'].values()] for p in routes.values()],
    'source_import_receipt':str(SRC/'source_assets_saved.json'),
    'next_target':'user review of ordinary Bed; other bed types retain their existing clips',
    'note':'User supplied the Meshy GLB after confirming paid membership and commercial-release needs. Sit_Lie_Bed is a seated leaning loop in this export. The separately named sleep clip contains seated support, backward movement, leg raising and lying down; its Meshy action ID is not inferred. The complete 5.7-second take is fitted after a 2.8-second seated approach and a 0.4-second join. Original GLB retained unchanged.'
})
(SRC/'source_request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
delivery={
    'source_file':inventory['file'],'source_sha256':inventory['sha256'],'selected_clip':'sleep',
    'source_timing_preserved':True,'bed_kind':'Bed','body_variants':['default','kaitlin'],
    'saved_gameplay_assets':6,'runtime_published':True,
    'durations_seconds':{'Enter':8.9,'Idle':4.,'Exit':9.2},
    'geometry':read(OUT/'geometry_audit_saved.json'),
    'hands_body':read(OUT/'hand_body_contact_saved.json'),
    'native_stage_joins':read(OUT/'native_stage_review.json'),
    'geometry_scope':'Jason native body/head and the two ordinary Bed meshes; Kaitlin checked for native skeleton, motion and stage joins, not skinned contacts or clothing combinations',
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),
    'full_cycle_preview':str(OUT/'ReviewSaved/bed_full_cycle.gif'),
    'preview_type':'offline render of saved compressed UE animation and actual project geometry',
    'game_tested':False,'multiplayer_tested':False,'interactive_editor_started':False,
    'git_commit':None,'git_push':None,
}
(OUT/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('MESHY_BED_DELIVERY_RECORDED',OUT/'delivery.json')
