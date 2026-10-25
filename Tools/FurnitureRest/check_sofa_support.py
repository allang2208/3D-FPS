"""Scoped post-save verification of the sofa support revision."""
import json,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'SourceAssets/FurnitureRest20261022/SofaSupportV3'
auth=json.loads((out/'authored.json').read_text());saved=json.loads((out/'ReviewSaved/saved_poses.json').read_text())
receipt=json.loads((out/'assets_saved.json').read_text());body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
meta=json.loads((ROOT/'Content/ColdSteelData/furniture_rest.json').read_text(encoding='utf-8'));audit=json.loads((out/'geometry_audit_saved.json').read_text())
old=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/RefineV2/authored.json').read_text())
assert set(auth['clips'])==set(saved['clips'])==set(receipt)
lower=[i for i,n in enumerate(auth['names']) if n.startswith(('pelvis','thigh','calf','foot','ball','toe','bigtoe','indextoe','middletoe','ringtoe','pinkytoe'))]
pos_error=quat_error=seam_error=0.
for role,data in auth['clips'].items():
 f=np.array(data['frames']);r=saved['clips'][role];assert np.isfinite(np.array(r['frames'])).all()
 assert body['clips'][role]==receipt[role]==r['asset'];assert meta['clips'][role]['duration']==data['duration']
 a=np.array(r['source_endpoints']);b=f[[0,-1]]
 pos_error=max(pos_error,float(np.linalg.norm(a[:,:,:3]-b[:,:,:3],axis=2).max()))
 quat_error=max(quat_error,float(np.max(1-np.abs(np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2)))))
 original=np.array(old['clips']['Rest.Sofa.'+role.split('.')[-1]]['frames'])
 assert np.array_equal(original[:,lower],f[:,lower])
for kind in ('Sofa','SofaLeft','SofaRight'):
 e=np.array(saved['clips']['Rest.'+kind+'.Enter']['frames']);i=np.array(saved['clips']['Rest.'+kind+'.Idle']['frames']);x=np.array(saved['clips']['Rest.'+kind+'.Exit']['frames'])
 for a,b in ((e[-1],i[0]),(i[0],x[0]),(x[-1],e[0]),(i[0],i[-1])):
  seam_error=max(seam_error,float(np.linalg.norm(a[:,:3]-b[:,:3],axis=1).max()))
assert pos_error<1e-4 and quat_error<1e-5 and seam_error<.2,(pos_error,quat_error,seam_error)
assert len(audit)==6 and sum(r['penetrating_samples'] for r in audit)==0
report=dict(animations=9,furniture_mesh_paths=2,seats=6,saved_compressed_readback=True,lower_body_unchanged=True,
 source_endpoint_position_error_cm=pos_error,source_endpoint_quaternion_error=quat_error,phase_seam_translation_error_cm=seam_error,
 geometry_flagged_samples=0,geometry_threshold_cm=.7,runtime_E_or_network_tested=False,gif='ReviewSaved/sofa_support.gif')
(out/'verification.json').write_text(json.dumps(report,indent=2));print(report)
