import json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
imp=json.loads((O/'import_receipt.json').read_text())
read=json.loads((O/'saved_readback.json').read_text())
review=json.loads((O/'UEReview/review.json').read_text())
auth=json.loads((O/'authoring.json').read_text())
cal=json.loads((O/'hip-calibration.json').read_text())
report={
 'task':'M24 sniper-referenced hip hold and V9 animation repair',
 'saved_asset_count':len(imp['saved']),'mesh':imp['mesh'],'clips':imp['clips'],
 'source_authored':True,'fbx_exported':True,'assets_imported_saved':imp['complete'],
 'outfit_registered':True,'runtime_paths_updated':True,
 'hip_presentation_offset_cm':cal['presentation_offset_cm'],
 'gun_local_up':[0,-1,0],
 'targeted_saved_pose_readback':read['complete'],
 'max_idle_source_error_cm':max(read['idle_source_error_cm'].values()),
 'max_return_to_hold_error_cm':max(v for row in read['returns_to_hold_cm'].values() for v in row.values()),
 'saved_sight_span_cm':read['sight_span_cm'],
 'editor_build':'Succeeded','build_log':'Saved/BuildEditor/build-20261027-131155.log',
 'offline_ue_render_complete':review['complete'],'offline_ue_render_count':len(review['views']),
 'corrective_driver_enabled':all(v['local_corrective_driver'] for v in review['views']),
 'm24_corrective_count':next(v['corrective_count'] for v in review['views'] if v['view']=='M24_idle_000'),
 'm24_max_corrective_delta_cm':next(v['max_morph_delta_cm'] for v in review['views'] if v['view']=='M24_idle_000'),
 'user_visual_accepted':False,'gameplay_tested':False,'pie_started':False,
 'limitations':['Offline posed scene only; live input, ADS transitions and multiplayer remain user testing.',
                'Aim clip was inspected in the same hip camera; no scope optical simulation in the offline capture.'],
 'source_hashes':{str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
  O.parent/'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx',
  O.parent/'M24CustomScope20261026/V9/M4_V9_Template.fbx',O/'M24_Hold_Editable.blend']}}
(O/'delivery_status.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_HOLD_DELIVERED',report['saved_asset_count'],report['offline_ue_render_count'],report['corrective_driver_enabled'])
