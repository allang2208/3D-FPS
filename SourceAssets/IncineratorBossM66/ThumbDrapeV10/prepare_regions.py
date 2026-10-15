"""Rebuild the anatomical selection inputs used by author_skin.py."""
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT=Path(__file__).resolve().parent/'Records'
data=np.load(ROOT/'source_arrays.npz');positions=data['positions']
_,ids,weld=np.unique(np.rint(positions/1e-6).astype(np.int64),axis=0,return_index=True,return_inverse=True)
points=positions[ids];edges=np.unique(np.sort(weld[data['edges']],axis=1),axis=0)
x,y,z=points.T
for mode in ('giant_hand','drape'):
    cut=((x<-.4)&(z>1.95)&(z<2.2)) if mode=='giant_hand' else (z>1.36)
    keep=~cut[edges].any(axis=1)
    graph=coo_matrix((np.ones(keep.sum()),(edges[keep,0],edges[keep,1])),shape=(len(points),len(points))).tocsr()
    _,labels=connected_components(graph,directed=False)
    if mode=='giant_hand':
        seed=np.linalg.norm(points-[-.95,.02,1.35],axis=1).argmin()
        np.save(ROOT/'giant_hand.npy',(labels==labels[seed])[weld])
    else:
        np.savez_compressed(ROOT/'topology.npz',weld=weld,unique_ids=ids,edges=edges,lower_component=labels)
