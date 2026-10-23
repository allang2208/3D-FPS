"""Publish the three checked motion profiles and the saved mountain/knit refit."""
import hashlib
import json
import runpy
import sys
from pathlib import Path
import numpy as np
from response_profiles import PROFILES

P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/BackpackMotion20261022'
fit_only='--fit-only' in sys.argv
plan=json.loads((R/'manifest.json').read_text())
saved=json.loads((R/'saved_assets.json').read_text())
refit=next(r for r in plan['variants'] if r['kind']=='mountain' and r['profile']=='knit_sweater')
digest=hashlib.sha256(Path(refit['source']).read_bytes()+Path(refit['mask']).read_bytes()).hexdigest()
written=saved['variants']['mountain/knit_sweater']
if written['asset']!=refit['asset'] or written['sha256']!=digest or not written['saved']:
    raise RuntimeError('Save the corrected mountain/knit mesh before routing the game to it')
path=P/'Content/ColdSteelData/player_body.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
owned=[];previous={}
for item,values in PROFILES.items():
    motion=cfg['outfits'][item]['backpack_motion'];previous[item]=dict(motion)
    if fit_only:continue
    bounds=[]
    for row in plan['variants']:
        if row['item']!=item:continue
        data=json.loads(Path(row['source']).read_text());v=np.array(data['positions'])
        rigid=v[np.unique(np.array(data['triangles'])[data['harness_face_count']:])]
        bounds.append((rigid.min(axis=0),rigid.max(axis=0)))
    motion.update(values)
    motion['bounds_min']=np.min([b[0] for b in bounds],axis=0).tolist()
    motion['bounds_max']=np.max([b[1] for b in bounds],axis=0).tolist()
    owned.extend(('outfits',item,'backpack_motion',key) for key in [*values,'bounds_min','bounds_max'])
    plan['settings'][item]=dict(motion)
cfg['outfits']['ue_mountain_backpack']['world_mesh_by_shirt']['ue_field_sweater']=refit['asset']
owned.append(('outfits','ue_mountain_backpack','world_mesh_by_shirt','ue_field_sweater'))
receipt=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](path,before,cfg,owned_paths=owned,producer=__file__)
if fit_only:plan['pending_response_tuning']=PROFILES
else:
    plan['response_tuning_revision']='BackpackResponseR2_20261022'
    plan.pop('pending_response_tuning',None)
plan['reset_on']=[s.replace('100ms','350ms') for s in plan['reset_on']]
plan['motion_limits']='same body/seam field; pinned chest hardware; rear support; smooth combined-displacement ceiling'
(R/'manifest.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
record=dict(revision='BackpackResponseR2_20261022',status='fit_saved_motion_pending_build' if fit_only else 'active',
    planned_profiles=PROFILES,before=previous,after={item:cfg['outfits'][item]['backpack_motion'] for item in PROFILES},
    config_receipt=receipt,reference_fit_audit=str(R/'response_fit_audit_r2_final.json'),
    refit_asset=written,native_response_diagnostic='Saved/BackpackMotionDiagnosis20261022/'+('native_response_initial_tuning.json' if fit_only else 'native_response.json'),
    final_driver_native_diagnostic_pending=fit_only,
    description={'ue_portable_backpack':'compact, firmer follow-through','ue_mountain_backpack':'slightly softer, larger movement',
                 'ue_expedition_backpack':'heavier, lower-frequency response with stronger damping'},
    visual_gameplay_accepted=False,player_profile_modified=False)
(R/'motion_response_r2.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('THREE_PACK_RESPONSE_R2_PUBLISHED',record['status'],receipt,flush=True)
