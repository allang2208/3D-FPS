"""Verify the scoped saved poses, phase handoffs and clearance measurements."""
import json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/HangingEntryV6'
source=json.loads((OUT/'authored.json').read_text());saved=json.loads((OUT/'ReviewSaved/saved_poses.json').read_text())
receipt=json.loads((OUT/'assets_saved.json').read_text());body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
assert set(source['clips'])==set(saved['clips'])
assert set(receipt)==set(source['changed_roles'])
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')};exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,ix,bind=[ns[k] for k in ('fk','ix','bind')]
rows=[];endpos=endrot=seampos=seamrot=0.
for role,d in source['clips'].items():
    s=saved['clips'][role];a=np.array(s['source_endpoints']);b=np.array(d['frames'])[[0,-1]]
    assert np.isfinite(np.array(s['frames'])).all()
    assert body['clips'][role]==s['asset']
    if role in receipt:assert body['clips'][role]==receipt[role]
    endpos=max(endpos,float(np.linalg.norm(a[:,:,:3]-b[:,:,:3],axis=2).max()))
    endrot=max(endrot,float(np.max(1-np.abs(np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2)))))
for kind in sorted({r.split('.')[1] for r in receipt}):
    clips={p:np.array(saved['clips'][f'Rest.{kind}.{p}']['frames']) for p in ('Enter','Idle','Exit')}
    for a,b in ((clips['Enter'][-1],clips['Idle'][0]),(clips['Idle'][0],clips['Exit'][0]),(clips['Idle'][0],clips['Idle'][-1]),(clips['Exit'][-1],clips['Enter'][0])):
        wa,wb=fk(a),fk(b);seampos=max(seampos,float(np.linalg.norm(wa[:,:3,3]-wb[:,:3,3],axis=1).max()))
        seamrot=max(seamrot,float(np.degrees(R.from_matrix(wa[:,:3,:3].transpose(0,2,1)@wb[:,:3,:3]).magnitude()).max()))
    f=clips['Idle'][0];w=fk(f)
    pelvis=w[ix['pelvis'],:3,:3]@bind[ix['pelvis'],:3,:3].T
    chest=w[ix['spine_03'],:3,:3]@bind[ix['spine_03'],:3,:3].T
    rows.append({'kind':kind,'pelvis_offset_cm':w[ix['pelvis'],:3,3].tolist(),
                 'foot_bone_height_cm':[float(w[ix['foot_'+s],2,3]) for s in ('l','r')],
                 'spine_pelvis_angle_deg':float(np.degrees(R.from_matrix(pelvis.T@chest).magnitude()))})
assert endpos<1e-4 and endrot<1e-5,(endpos,endrot)
assert seampos<.25 and seamrot<.5,(seampos,seamrot)
audit=json.loads((OUT/'geometry_audit_saved.json').read_text())
assert len(audit)==9 and sum(row['penetrating_samples'] for row in audit)==0
report={'animations':len(receipt),'meshes':3,'seats':len(audit),'source_endpoint_error_cm':endpos,
        'source_endpoint_quaternion_error':endrot,'compressed_handoff_error_cm':seampos,
        'compressed_handoff_error_deg':seamrot,'geometry_threshold_cm':.7,'geometry_flagged_samples':0,
        'idle_poses':rows,'gameplay_tested':False}
old=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/RelaxedSeatV5/authored.json').read_text())
fixed=[i for i,n in enumerate(source['names']) if not n.startswith(('clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_'))]
for role,take in source['clips'].items():
    a=np.array(take['frames']);b=np.array(old['clips'][role]['frames'])
    assert np.array_equal(a[:,fixed],b[:,fixed]),role
    if role.endswith('.Idle'):assert np.array_equal(a,b),role
report.update(idle_reused=6,reviewed_clips=18,lower_body_and_spine_unchanged=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
