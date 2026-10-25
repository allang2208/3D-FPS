"""Requested source check: reference contacts and rigid/harness seam ownership."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'manifest.json')
report={'revision':plan['revision'],'scope':'author geometry, reference pose, both bodies and current garment/waist routes',
        'runtime_tested':False,'network_tested':False,'profiles':[]}
source=np.load(R/'Authored/static_source.npz');worn=np.load(R/'Authored/worn_body.npz')
report['source']={'display_triangles':len(source['triangles']),'worn_triangles':len(worn['triangles']),
                  'faces_preserved':bool(np.array_equal(source['triangles'],worn['triangles'])),
                  'uv_preserved':bool(np.array_equal(source['uv'],worn['uv'])),
                  'outer_face':'-Y','wearer_face':'+Y'}
for row in plan['variants']:
    data=read(Path(row['source']));v=np.asarray(data['positions']);f=np.asarray(data['triangles'],int)
    normal=read(R/'BodyInputs/Normalized'/row['rig']/'body.json')
    native=read(R/'BodyInputs'/read(R/'BodyInputs/manifest.json')['rigs'][row['rig']]['body'])
    male=read(R/'BodyInputs/Normalized/Jason/body.json')['reference']['spine_04']
    target=native['reference']['spine_04']
    rotation=Rotation.from_quat(row.get('body_native_rotation_quat',row['rigid_rotation_quat'])).as_matrix().T
    translation=np.asarray(target[:3])-np.asarray(male[:3])@rotation
    canonical=(v-translation)@rotation.T
    eq=read(R/'Envelopes'/(row['profile']+'.json'))
    samples=np.vstack([canonical,canonical[f].mean(axis=1)])
    clearance=np.full(len(samples),np.inf)
    for raw in eq['cells']:
        cell=np.asarray(raw)
        for start in range(0,len(samples),1024):
            part=samples[start:start+1024]
            depth=(part@cell[:,:3].T+cell[:,3]).max(axis=1)
            clearance[start:start+len(part)]=np.minimum(clearance[start:start+len(part)],depth)
    mask=np.asarray(data['motion_mask']);seams=[]
    s3=next(b['index'] for b in data['bones'] if b['name']=='spine_03')
    for part in data['parts']:
        if 'sewn_bag_points' not in part:continue
        ids=part['rows'][0]+part['rows'][-1]
        seams.append({'part':part['name'],'mask_min':float(mask[ids].min()),
                      'spine_03_min':min(dict(data['weights'][i]).get(s3,0) for i in ids),
                      'endpoint_error_cm':float(np.max(np.linalg.norm(np.asarray(part['path'])[[0,-1]]-part['sewn_bag_points'],axis=1)))})
    record={'profile':row['profile'],'vertex_and_face_samples':len(samples),
            'inside_reference_envelope':int((clearance<-.02).sum()),'minimum_plane_clearance_cm':float(clearance.min()),
            'seams':seams,'weight_sum_error':max(abs(sum(w for _,w in weights)-1) for weights in data['weights']),
            'triangles':len(f)}
    report['profiles'].append(record)
    print('PATHFINDER_REFERENCE_CHECK',row['profile'],record['inside_reference_envelope'],round(record['minimum_plane_clearance_cm'],4),flush=True)
(R/'reference_inspection.json').write_text(json.dumps(report,indent=2))
