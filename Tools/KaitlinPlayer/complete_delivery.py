"""Record production receipts separately from runtime acceptance."""
import datetime,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
publications={part:read(W/(part+'_publication.json')) for part in ('furniture','packs')}
rows=read(W/'Packs/manifest.json');saved=read(W/'Packs/saved_assets.json')
builds={target:str(P/'SourceAssets/KaitlinPlayer20261023'/('build-completion-20261024-'+target+'.txt')) for target in ('FPSGAMEEditor','FPSGAME')}
for path in builds.values():
    if 'Result: Succeeded' not in Path(path).read_text('utf-8',errors='replace'):raise RuntimeError('Build receipt incomplete')
for row in rows:
    if saved[row['rig']+'/'+row['item']]!=row['asset']+'.'+row['asset'].rsplit('/',1)[-1]:raise RuntimeError('Unfinished pack save revision')
report={
    'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    'implementation_complete':True,'runtime_accepted':False,
    'network':{'old_mirror_preserves_owner_head_and_hair':True,'inventory_fast_path_requires_uploaded_appearance':True,
        'inventory_receipts_do_not_acknowledge_unsent_cosmetics':True,'heartbeat_inventory_campfire_capture_matching_cosmetic_identity':True,
        'new_rpc_or_save_schema':False},
    'furniture':{'roles_published':len(read(W/'Furniture/saved_assets.json')),
        'newly_retargeted_enter_exit_clips':12,'unchanged_saved_idle_clips_reused':6,
        'female_eye_tracks':len(read(W/'Furniture/camera_tracks.json')),
        'diagnosis':'Isolated body animation graph evaluated Chair/Sofa/Bed for Jason->Kaitlin->Jason, with native postprocess enabled/disabled. Female poses play. This does not exercise E-key focus/StartRest or network transport.',
        'diagnosis_receipt':'SourceAssets/KaitlinFurniture20261024/pipeline-resume-20261024.json'},
    'packs':{'new_meshes':len(rows),'per_body':{rig:sum(r['rig']==rig for r in rows) for rig in ('Jason','Kaitlin')},
        'shirt':'ue_work_jacket','revision':'WorkJacketR2','native_weights_uvs_materials_motion_masks_preserved':True,
        'new_degenerate_faces':sum(r['geometry_receipt']['new_degenerate_faces'] for r in rows),
        'rigid_body_offsets_and_sling_tethers_published':True,'saved_assets':saved,
        'first_fit':'Preserved but not published; the R2 polar deformation cage replaces per-vertex projection to avoid flattening strap faces.'},
    'publication_receipts':publications,'build_receipts':builds,
    'not_run':['interactive editor','game or PIE','actual host/client transport','late join/reconnect/respawn/travel gameplay','visual clipping/hair-distance/face-reference acceptance'],
    'remaining_acceptance':['Actual E-key furniture entry/exit on each body','Host/guest appearance switching followed immediately by inventory operations','Late mirror, late join, reconnect, respawn and team travel','Jacket straps during running/resting and native face/hair appearance'],
    'source_input_note':'Two capture batches wrote their data before a Python shutdown exception. All saved input hashes were retained; the resumed producer finished with exit 0. Final asset saves are recorded separately.',
    'git_committed_or_pushed':False}
(W/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('KAITLIN_COMPLETION_DELIVERY',len(rows),'pack meshes,',report['furniture']['roles_published'],'furniture roles, two successful build targets')
