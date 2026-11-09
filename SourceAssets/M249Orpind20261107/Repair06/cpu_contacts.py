"""Contact check of native render vertices, including V9 joint morphs."""
from pathlib import Path
import sys,json
import numpy as np
import trimesh
from contact_sweep import intersect

folder=Path(sys.argv[1])
faces=np.fromfile(folder/'surface.indices',dtype=np.uint32).reshape(-1,3)
materials=np.fromfile(folder/'surface.materials',dtype=np.uint32)
left=np.fromfile(folder/'surface.left',dtype=np.uint8)>0
lf=faces[left[faces].all(1)]
of=faces[np.isin(materials,[14,16])]
result={}
for file in sorted(folder.glob('*.vertices')):
    v=np.fromfile(file,dtype=np.float32).reshape(-1,3).astype(np.float64)
    optic=trimesh.Trimesh(v,of,process=False);tree=optic.triangles_tree;tri=v[of]
    lo=tri.min((0,1));hi=tri.max((0,1));hand=v[lf];mins=hand.min(1);maxs=hand.max(1)
    near=np.nonzero(((maxs>=lo)&(mins<=hi)).all(1))[0];hits=[]
    for j in near:
        for k in tree.intersection(np.r_[mins[j],maxs[j]]):
            if intersect(hand[j],tri[k]):hits.append(int(j));break
    result[file.stem]={'intersecting_hand_triangles':len(hits)}
(folder/'native_contacts.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result),flush=True)
