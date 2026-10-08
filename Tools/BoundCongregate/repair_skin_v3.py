"""Diffuse the existing anatomical weights across welded surface joints."""
from pathlib import Path
import json
import numpy as np
from scipy.sparse import coo_matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'RigRepairV3';OUT.mkdir(exist_ok=True)
data=np.load(ROOT/'Assessment/output.npz');skin=np.load(ROOT/'Authoring/skin_weights.npz')
vertices,inverse=np.unique(np.round(data['vertices'],5),axis=0,return_inverse=True)
tri=inverse[data['triangles']]
edges=np.unique(np.sort(np.concatenate((tri[:,:2],tri[:,1:],tri[:,[0,2]])),axis=1),axis=0)
edges=edges[edges[:,0]!=edges[:,1]]
count=len(vertices);names=skin['names']
base=np.zeros((len(inverse),len(names)),np.float32)
base[np.arange(len(inverse))[:,None],skin['indices']]=skin['weights']
weights=np.zeros((count,len(names)),np.float32);np.add.at(weights,inverse,base)
weights/=np.bincount(inverse)[:,None]
rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]]
degree=np.bincount(rows,minlength=count)
adj=coo_matrix((np.ones(len(rows),np.float32)/degree[rows],(rows,cols)),shape=(count,count)).tocsr()
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text())
joints=np.array([b['head'] for b in recipe['bones'] if b['name'] not in ('root','body')])
distance=np.sqrt(((vertices[:,None]-joints[None])**2).sum(2)).min(1)
strength=(32+360*np.clip(1-distance/.18,0,1)**2).astype(np.float32)[:,None]
# Preserve the original surface-geodesic anatomical assignment. Nearby donor
# limbs and organs must not receive weights from a different limb merely because
# their Euclidean capsules happen to be close.
source=weights.copy()
for i in range(180): weights=(source+strength*(adj@weights))/(1+strength)
ids=np.argsort(weights,axis=1)[:,-8:]
values=np.take_along_axis(weights,ids,axis=1);values/=values.sum(1,keepdims=True)
np.savez_compressed(OUT/'skin_weights.npz',indices=ids[inverse],weights=values[inverse],names=names)
print('JOINT_WEIGHTS_SAVED',count,len(inverse),flush=True)
