"""Compare published UE pose readback with authoring data and phase contacts."""
import json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/RefineV2'
auth=json.loads((OUT/'authored.json').read_text());saved=json.loads((OUT/'ReviewSaved/saved_poses.json').read_text())
config=json.loads((OUT/'furniture_rest.json').read_text(encoding='utf-8'))
runtime=json.loads((ROOT/'Content/ColdSteelData/furniture_rest.json').read_text(encoding='utf-8'))
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
receipt=json.loads((OUT/'assets_saved.json').read_text())
assert config==runtime and auth['names']==saved['names']
assert set(auth['clips'])==set(receipt) and set(receipt)<=set(saved['clips'])
rows=[]
def error(a,b):
 a=np.array(a);b=np.array(b)
 return float(np.max(np.linalg.norm(a[:,:3]-b[:,:3],axis=1))),float(np.max(1-np.abs(np.sum(a[:,3:7]*b[:,3:7],axis=1))))
for role,data in saved['clips'].items():
 if role not in receipt:continue
 frames=np.array(data['frames']);a=auth['clips'][role]
 assert body['clips'][role]==receipt[role]==data['asset']
 assert np.isfinite(frames).all() and np.max(np.abs(np.linalg.norm(frames[:,:,3:7],axis=2)-1))<1e-5
 assert abs(data['duration']-a['duration'])<1e-5
 e=[error(data['source_endpoints'][i],a['frames'][i]) for i in (0,-1)]
 assert max(x[0] for x in e)<1e-4 and max(x[1] for x in e)<1e-5
 rows.append(dict(role=role,asset=data['asset'],duration=data['duration'],endpoint_translation_error_cm=max(x[0] for x in e)))
for kind in config['types']:
 enter=saved['clips'][f'Rest.{kind}.Enter']['frames'];idle=saved['clips'][f'Rest.{kind}.Idle']['frames'];leave=saved['clips'][f'Rest.{kind}.Exit']['frames']
 for a,b in ((enter[-1],idle[0]),(idle[0],idle[-1]),(idle[0],leave[0]),(leave[-1],enter[0])):
  pos,q=error(a,b);assert pos<.2 and q<1e-4,(kind,pos,q)
audit=json.loads((OUT/'geometry_audit_saved.json').read_text())
assert len({r['mesh'] for r in audit})==len(config['furniture'])
assert not any(r['penetrating_samples'] for r in audit), 'Furniture contacts still require repair'
assert min(r['entry_capsule_geometry_clearance_cm'] for r in audit)>0
assert min(r['minimum_body_z'] for r in audit)>-.1
report=dict(date='2026-10-23',saved_animation_count=len(rows),furniture_mesh_paths=len(config['furniture']),
 body_asset=saved['mesh'],
 slot_checks=len(audit),phase_seams_pass=True,readback_pass=True,clips=rows,
 geometry_sample_scope='Saved compressed poses, approximately 7.5 Hz; body vertex stride 4 and head stride 20; 0.7 cm candidate threshold with three ray parity votes. Final visual review covers full enter/idle/exit GIFs.',
 geometry_flagged_samples=sum(r['penetrating_samples'] for r in audit),
 authored_sha256=hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest(),
 runtime_input_or_multiplayer_tested=False,preview='Actual project geometry and saved UE animations rendered offline with neutral materials.')
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('REST_REFINEMENT_READBACK_VERIFIED',len(rows),'clips,',len(audit),'slots; flagged geometry samples',report['geometry_flagged_samples'])
