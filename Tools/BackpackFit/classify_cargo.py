"""Separate whole cargo islands from the sewn end caps of mixed-mask straps."""
import json,os
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
R=Path(os.environ['BACKPACK_FIT_RUN_DIR']);records=json.loads((R/'captured.json').read_text());out=R/'CargoMasks';out.mkdir(exist_ok=True)
for record in records.values():
    if not record.get('mask_valid'):continue
    folder=Path(record['folder']);v=np.fromfile(folder/'positions.bin',dtype='<f4').reshape(-1,3);f=np.fromfile(folder/'triangles.bin',dtype='<i4').reshape(-1,3);mask=np.fromfile(folder/'mask.bin',dtype='<f4')
    _,inverse=np.unique(np.round(v,4),axis=0,return_inverse=True);faces=inverse[f];n=inverse.max()+1
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(n,n)).tocsr()
    count,labels=connected_components(graph,directed=False);labels=labels[inverse];minimum=np.full(count,1.);np.minimum.at(minimum,labels,mask)
    cargo=(minimum[labels]>.98).astype('u1');file=out/(record['key']+'.bin');cargo.tofile(file);record['cargo_vertices']=str(file)
(R/'captured.json').write_text(json.dumps(records,indent=2))
print('BACKPACK_CARGO_ISLANDS_CLASSIFIED')
