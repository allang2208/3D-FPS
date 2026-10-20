"""Show actual compressed source + profile at the previously missed times."""
from diagnose_recovery import O,R5,s
import json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
capture=json.loads((R5/'native-saved-glove.json').read_text())['families'][0]
hip=s.matrices([capture['view_to_camera']])[0];dense=np.load(O/'dense-review.npz')
data={'frames':{},'triangles':{'bare':s.arms['triangles'],
    'gun':[t for t,m in zip(s.weapon['triangles'],s.weapon['material_ids']) if m>=2 and m not in (5,7)]},'camera_vertical_fov':75.}
surfaces={'bare':s.bare,'gun':s.Surface(s.weapon)}
for frame in [67.,67.25,67.5,67.75,68.,68.5]:
    k=int(np.argmin(abs(dense['frames']-frame)));t=frame/120.;x=np.clip((t/.9-.6)/.4,0,1)
    alpha=min(1-np.exp(-16*t),1-x*x*x*(10+x*(-15+6*x)))
    view=hip.copy();view[:3,3]=(1-alpha)*hip[:3,3]+alpha*np.array([10.,0.,-5.])
    view[:3,:3]=Slerp([0,1],R.from_matrix([hip[:3,:3],R.from_euler('z',90,degrees=True).as_matrix()]))([alpha]).as_matrix()[0]
    def transform(v):
        c=v@view[:3,:3].T+view[:3,3]
        return np.stack([c[...,1],c[...,0],c[...,2]],axis=-1).tolist()
    data['frames'][str(frame)]={}
    for label,field in [('R5','before'),('R6','after')]:
        p=dense[field][k];data['frames'][str(frame)][label]={n:transform(surface.evaluate(p)) for n,surface in surfaces.items()}
with gzip.open(O/'review-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('COMPRESSED_SUBFRAME_REVIEW_PREPARED',flush=True)
