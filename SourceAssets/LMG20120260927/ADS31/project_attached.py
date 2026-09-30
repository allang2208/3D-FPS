import json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
d=json.loads((O/'aim.json').read_text()); a=np.load(O/'projected.npz'); p=json.loads((O/'projection.json').read_text())
t=d['aim']['WPN_root']; root=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s'])
q=p['view_rotation']; R=Rotation.from_quat([*q[1:],q[0]]).as_matrix(); loc=np.array(p['eye_offset'])
out={}; points=[a['points']]; faces=[a['faces']]; mi=[a['material_ids']]; names=list(a['material_names']); offset=len(a['points'])
for name,mesh in json.loads((O/'attached.json').read_text()).items():
    v=np.array(mesh['vertices']); tri=np.array(mesh['triangles'])
    if name=='FrontSight':v=v*.01+np.array([.0008,.54212,.0648])
    elif name=='RearSight':v=v*.01+np.array([.0008,-.04252,.0855])
    else:
        if name=='BipodLegA':v+=np.array([1.356,46.498,-1.398])
        if name=='BipodLegB':v+=np.array([-1.196,46.498,-1.398])
        v*=.01
    v=(v@root.T+np.array(t['p']))@R.T+loc
    points.append(v); faces.append(tri+offset); mi.append(np.full(len(tri),len(names))); names.append(name); offset+=len(v)
    out[name]={'bounds_camera_cm':[[float(v[:,k].min()),float(v[:,k].max())] for k in range(3)]}
np.savez_compressed(O/'projected_complete.npz',points=np.concatenate(points),faces=np.concatenate(faces),material_ids=np.concatenate(mi),material_names=np.array(names))
(O/'attached_projection.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
