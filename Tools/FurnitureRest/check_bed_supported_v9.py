"""Verify saved bed phases, eye tracks, exact reverse exits and contacts."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9';BASE=OUT.parent/'BedBaseline20261023'
source=json.loads((OUT/'authored.json').read_text());saved=json.loads((OUT/'ReviewSaved/saved_poses.json').read_text())
receipt=json.loads((OUT/'assets_saved.json').read_text());body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
inventory=json.loads((BASE/'inventory.json').read_text(encoding='utf-8'));kinds=inventory['types']
assert set(source['clips'])==set(saved['clips'])==set(receipt) and len(receipt)==18
assert body['body_mesh']==source['mesh']
configs={n:json.loads((ROOT/'Content/ColdSteelData'/n).read_text(encoding='utf-8-sig')) for n in ('furniture_rest.json','apartment_furniture_rest.json')}
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')};exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,ix,bind,palm=[ns[n] for n in ('fk','ix','bind','palm')]
pos_error=quat_error=seampos=seamrot=0.;rows=[]
for role,take in source['clips'].items():
    raw=np.array(take['frames']);read=saved['clips'][role]
    assert receipt[role]==body['clips'][role]==read['asset']
    assert np.isfinite(np.array(read['frames'])).all()
    assert abs(read['duration']-take['duration'])<1e-5
    cfg=configs['apartment_furniture_rest.json' if 'Apartment' in role else 'furniture_rest.json']['clips'][role]
    assert abs(cfg['duration']-take['duration'])<1e-6 and len(cfg['camera'])==len(raw)
    a=np.array(read['source_endpoints']);b=raw[[0,-1]]
    pos_error=max(pos_error,float(np.linalg.norm(a[:,:,:3]-b[:,:,:3],axis=2).max()))
    quat_error=max(quat_error,float(np.max(1-np.abs(np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2)))))
    for index in (0,len(raw)//2,len(raw)-1):
        w=fk(raw[index]);h=w[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
        assert np.linalg.norm(eye-np.array(cfg['camera'][index][:3]))<1e-5
for kind in kinds:
    e=np.array(source['clips'][f'Rest.{kind}.Enter']['frames']);x=np.array(source['clips'][f'Rest.{kind}.Exit']['frames'])
    assert np.array_equal(x[:len(e)],e[::-1]) and np.array_equal(x[len(e):],np.repeat(e[:1],9,axis=0))
    clips={p:np.array(saved['clips'][f'Rest.{kind}.{p}']['frames']) for p in ('Enter','Idle','Exit')}
    for a,b in ((clips['Enter'][-1],clips['Idle'][0]),(clips['Idle'][0],clips['Exit'][0]),(clips['Idle'][0],clips['Idle'][-1]),(clips['Exit'][-1],clips['Enter'][0])):
        wa,wb=fk(a),fk(b);seampos=max(seampos,float(np.linalg.norm(wa[:,:3,3]-wb[:,:3,3],axis=1).max()))
        seamrot=max(seamrot,float(np.degrees(R.from_matrix(wa[:,:3,:3].transpose(0,2,1)@wb[:,:3,:3]).magnitude()).max()))
    w=fk(clips['Idle'][0]);fore=w[ix['hand_l'],:3,3]-w[ix['lowerarm_l'],:3,3]
    forward=w[ix['hand_l'],:3,:3]@bind[ix['hand_l'],:3,:3].T@palm['l'][:,1]
    rows.append({'kind':kind,'rest_left_wrist_angle_deg':float(np.degrees(np.arccos(np.clip(fore@forward/np.linalg.norm(fore),-1,1)))),
                 'enter_seconds':source['clips'][f'Rest.{kind}.Enter']['duration'],'exit_seconds':source['clips'][f'Rest.{kind}.Exit']['duration']})
assert pos_error<1e-4 and quat_error<1e-5 and seampos<.25 and seamrot<.5,(pos_error,quat_error,seampos,seamrot)
audit=json.loads((OUT/'geometry_audit_saved.json').read_text());contacts=json.loads((OUT/'hand_body_contact_saved.json').read_text())
assert len(audit)==len(inventory['furniture'])==11 and sum(r['penetrating_samples'] for r in audit)==0
assert len(contacts)==6 and sum(r['penetrating_samples'] for r in contacts)==0
report={'saved_animations':18,'bed_types':6,'bed_meshes':11,'phase_handoff_error_cm':seampos,'phase_handoff_error_deg':seamrot,
        'source_endpoint_error_cm':pos_error,'source_endpoint_quaternion_error':quat_error,'furniture_sample_threshold_cm':.7,
        'furniture_penetrating_samples':0,'hand_body_threshold_cm':.5,'hand_body_penetrating_samples':0,
        'exit_is_reversed_entry':True,'eye_tracks_updated':True,'poses':rows,'gameplay_or_network_tested':False,
        'head_geometry':'runtime skeletal weights; copied body ancestors; neutral face',
        'saved_motion_sampling_hz':15,'head_support_gap_by_mesh':[{k:r[k] for k in ('mesh','head_support_gap_cm')} for r in audit],
        'heel_support_gap_by_type':json.loads((OUT/'heel_support_saved.json').read_text())}
report['knee_hinges']=json.loads((OUT/'leg_hinges_saved.json').read_text())
report['buttock_support']=json.loads((OUT/'seat_support_saved.json').read_text())
assert all(r['maximum_knee_off_hinge_degrees']<.5 and r['bone_length_error_cm']<.01 for r in report['knee_hinges']['current'])
report['sofa_entry_reference']='HangingEntryV6 / Rest.Sofa.Enter / 0 to 1.15 seconds'
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
