"""Separate the actual distal small-arm surface across the elbow cross-section.

Work on welded adjacency, not UV charts or the already contaminated bone labels.
This is an authoring selection only; exported geometry is not cut or welded.
"""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parent
data=np.load(ROOT/'Records/anatomy_arrays.npz')
positions=data['positions'];weld=data['weld'];unique=data['unique_ids']
points=positions[unique];edges=np.unique(np.sort(weld[data['edges']],axis=1),axis=0)
x,y,z=points.T
# The forearm joins the armpit web above this cross-section. The fingers and
# oral lining below it are distinct surfaces, despite overlapping in projection.
section=(x>.40)&(z>2.05)&(z<2.25)
kept=(~section[edges].any(axis=1))&(edges[:,0]!=edges[:,1])
graph=coo_matrix((np.ones(kept.sum()),(edges[kept,0],edges[kept,1])),shape=(len(points),len(points))).tocsr()
_,labels=connected_components(graph,directed=False)
palm_seed=int(np.linalg.norm(points-[.38,-.63,1.64],axis=1).argmin())
hand=labels==labels[palm_seed]
# Tiny detached surface fragments inherit the adjacent anatomical surface.
# Never bridge the large mouth component into the hand using distance alone.
main=data['component_ids'][unique]==0
tree=cKDTree(points[main]);main_ids=np.flatnonzero(main)
distance,nearest=tree.query(points[~main])
hand[np.flatnonzero(~main)]=hand[main_ids[nearest]]&(distance<.025)
np.save(ROOT/'Records/small_arm_surface.npy',hand[weld])
report={'method':'welded surface connectivity below elbow; no geometry mutation',
        'seed_position':points[palm_seed].tolist(),'hand_vertices':int(hand[weld].sum()),
        'hand_bounds':[points[hand].min(0).tolist(),points[hand].max(0).tolist()],
        'reported_stretched_vertices_in_hand':{str(i):bool(hand[weld[i]]) for i in (80049,82176,52089,53114)}}
(ROOT/'Records/surface_ownership.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_SMALL_ARM_OWNERSHIP '+json.dumps(report))
