"""Add unchanged left glove surfaces to the requested belt-contact frames."""
import sys,gzip,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'ClothReload44/Diagnostics'))
import diag_lib as D
T=D.load_tracks(O.parent/'ClothReload44/Tracks/base_tracks.json.gz')
frames=[209,458,489,526,574];W=D.worlds(T,frames)
skin=D.load_json_mesh(D.SA/'BlackLeatherDetail20260928/StitchWearV4/Authored/PKM.json')
left=np.array([n.endswith('_l') for n in D.NAMES])[skin.dom]
tri=skin.tris[np.all(left[skin.tris],axis=1)];ids=np.unique(tri);tr=np.searchsorted(ids,tri)
for j,fi in enumerate(frames):
 with gzip.open(O/'Inspection'/('after_%d.json.gz'%fi),'rt') as f:parts=json.load(f)
 g=np.linalg.inv(W[j,D.BI['WPN_root']]);p=skin.pose(W[j],ids);p=p@g[:3,:3].T+g[:3,3]
 parts.append({'p':p.tolist(),'t':tr.tolist(),'role':'Glove'})
 with gzip.open(O/'Inspection'/('contact_%d.json.gz'%fi),'wt') as f:json.dump(parts,f)
print('B53_CONTACT_FRAMES')
