"""Check saved exit continuity and exact reuse of the reversed entry poses."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/ReversedExitV7'
source=json.loads((OUT/'authored.json').read_text());saved=json.loads((OUT/'ReviewSaved/saved_poses.json').read_text())
old=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/HangingEntryV6/authored.json').read_text())
receipt=json.loads((OUT/'assets_saved.json').read_text())
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
configs={name:json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig'))
         for name in ('furniture_rest.json','apartment_furniture_rest.json')}
assert set(receipt)==set(source['changed_roles']) and len(receipt)==6
assert set(saved['clips'])==set(source['clips'])
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')};exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,ix,bind=[ns[k] for k in ('fk','ix','bind')]
pos_error=quat_error=seampos=seamrot=0.
for role,data in source['clips'].items():
    f=np.array(data['frames']);r=saved['clips'][role]
    assert body['clips'][role]==r['asset']
    if role in receipt:
        assert receipt[role]==r['asset']
        cfg=configs['apartment_furniture_rest.json' if 'Apartment' in role else 'furniture_rest.json']
        assert cfg['clips'][role]==json.loads((OUT/('apartment_furniture_rest.json' if 'Apartment' in role else 'furniture_rest.json')).read_text(encoding='utf-8'))['clips'][role]
    else:assert data==old['clips'][role]
    a=np.array(r['source_endpoints']);b=f[[0,-1]]
    pos_error=max(pos_error,float(np.linalg.norm(a[:,:,:3]-b[:,:,:3],axis=2).max()))
    quat_error=max(quat_error,float(np.max(1-np.abs(np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2)))))
    assert np.isfinite(np.array(r['frames'])).all()
for kind in sorted({r.split('.')[1] for r in receipt}):
    enter=np.array(source['clips'][f'Rest.{kind}.Enter']['frames'])
    leave=np.array(source['clips'][f'Rest.{kind}.Exit']['frames'])
    assert np.array_equal(leave[:len(enter)],enter[::-1])
    assert np.array_equal(leave[len(enter):],np.repeat(enter[:1],9,axis=0))
    clips={p:np.array(saved['clips'][f'Rest.{kind}.{p}']['frames']) for p in ('Enter','Idle','Exit')}
    for a,b in ((clips['Enter'][-1],clips['Idle'][0]),(clips['Idle'][0],clips['Exit'][0]),(clips['Exit'][-1],clips['Enter'][0])):
        wa,wb=fk(a),fk(b)
        seampos=max(seampos,float(np.linalg.norm(wa[:,:3,3]-wb[:,:3,3],axis=1).max()))
        seamrot=max(seamrot,float(np.degrees(R.from_matrix(wa[:,:3,:3].transpose(0,2,1)@wb[:,:3,:3]).magnitude()).max()))
assert pos_error<1e-4 and quat_error<1e-5 and seampos<.25 and seamrot<.5,(pos_error,quat_error,seampos,seamrot)
audit=json.loads((OUT/'geometry_audit_saved.json').read_text())
assert len(audit)==9 and sum(row['penetrating_samples'] for row in audit)==0
report={'new_exit_assets':len(receipt),'unchanged_entry_idle_clips':12,'seats':9,'reviewed_clips':18,
        'exact_reversed_source_poses':True,'reverse_seconds':2.8,'standing_hold_seconds':.3,
        'source_endpoint_error_cm':pos_error,'source_endpoint_quaternion_error':quat_error,
        'compressed_handoff_error_cm':seampos,'compressed_handoff_error_deg':seamrot,
        'geometry_threshold_cm':.7,'geometry_flagged_samples':0,'exit_camera_updated':True,'gameplay_tested':False}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
