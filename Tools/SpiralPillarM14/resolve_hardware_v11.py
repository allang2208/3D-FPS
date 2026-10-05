"""Resolve welded metal islands and their mixed skinning for the chain repair."""
from pathlib import Path
import json, numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/ProductionV11/Records')
d=np.load(ROOT/'hardware_source.npz');info=json.loads((ROOT/'hardware_source.json').read_text())
p=d['p'];f=d['f'];metal=d['metal'];selected=d['selected']
_,inverse=np.unique(np.round(p*100000).astype(np.int64),axis=0,return_inverse=True)
mf=inverse[f[metal]]
vertices,mapping=np.unique(mf,return_inverse=True);tri=mapping.reshape(-1,3)
rows=tri[:,[0,1,2]].ravel();cols=tri[:,[1,2,0]].ravel()
graph=coo_matrix((np.ones(len(rows),np.uint8),(rows,cols)),shape=(len(vertices),len(vertices))).tocsr()
count,components=connected_components(graph,directed=False)
face_comp=components[tri[:,0]];sizes=np.bincount(face_comp)
records=[]
mf_original=f[metal]
for index in np.argsort(sizes)[::-1][:75]:
    points=p[np.unique(mf_original[face_comp==index])]
    records.append({'id':int(index),'triangles':int(sizes[index]),'center':points.mean(0).tolist(),
                    'min':points.min(0).tolist(),'max':points.max(0).tolist()})
groups=info['groups'];bone_names=np.array(groups+['none'])
metal_group=np.array([name.startswith('chain_') or name=='restraint' for name in groups]+[False])
bad=np.sum(d['weights']*~metal_group[d['bones']],axis=1)
report={'components':count,'largest':records,'metal_vertices_with_tissue_weight':int((bad>.01).sum()),
        'metal_vertices_with_multiple_weights':int(((d['weights']>.01).sum(1)>1).sum())}
(ROOT/'hardware_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
np.savez(ROOT/'hardware_components.npz',weld=inverse,metal_face_components=face_comp,component_sizes=sizes)
print(json.dumps({**report,'largest':records[:18]},indent=2))
