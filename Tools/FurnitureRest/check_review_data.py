"""Check saved asset readback against authored endpoints; record visual findings separately."""
import json
from pathlib import Path
import numpy as np
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022')
out=ROOT/'Review20261023';saved=json.loads((out/'saved_poses.json').read_text());source=json.loads((ROOT/'authored.json').read_text())
rows=[]
for role,data in saved['clips'].items():
 f=np.asarray(data['frames']);original=np.asarray(source['clips'][role]['frames'])
 a=f[[0,-1]];b=original[[0,-1]]
 rows.append({'role':role,'duration':data['duration'],'finite':bool(np.isfinite(f).all()),
  'max_quaternion_norm_error':float(np.max(np.abs(np.linalg.norm(f[:,:,3:7],axis=2)-1))),
  'endpoint_translation_error_cm':float(np.max(np.linalg.norm(a[:,:,:3]-b[:,:,:3],axis=2))),
  'endpoint_quaternion_error':float(np.max(1-np.abs(np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2))))})
report={'date':'2026-10-23','saved_asset_readback':True,'body_asset':saved['mesh'],'clips':rows,
 'preview':'Saved native animation keys and actual body/furniture geometry; neutral Blender materials, no runtime E-input recording. Floor offset and two-bone foot correction reproduced for chairs/sofas. Separate source head surface follows the head bone; no hair/facial animation.',
 'visual_result':'not_accepted','findings':['Sofa lower legs penetrate cushion/front edge; seat anchor is too far back.','Bed entry/exit places standing/sitting body through mattress instead of an authored side-entry route.','Hand/wrist orientations look over-rotated; contact/support and weight transfer need work.','Bunk entry/exit requires a side route clear of the ladder/frame.'],
 'production_assets_modified':False,'gameplay_E_interaction_tested':False,'multiplayer_tested':False}
(out/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Readback clips:',len(rows),'finite:',all(r['finite'] for r in rows),'maximum endpoint translation error cm:',max(r['endpoint_translation_error_cm'] for r in rows))
