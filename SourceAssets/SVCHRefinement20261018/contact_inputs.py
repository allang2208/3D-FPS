"""Numerical authoring inputs, in UE receiver-bind centimetres."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
SRC=O.parent/'SVCHSketchfab20261017'
D=json.loads((O/'runtime_inputs.json').read_text())
N=D['meshes']['svd']['names']; PI=[N.index(p) if p in N else -1 for p in D['meshes']['svd']['parents']]
def matrices(rows):
    rows=np.asarray(rows); out=np.broadcast_to(np.eye(4),(len(rows),4,4)).copy()
    out[:,:3,:3]=Rotation.from_quat(rows[:,3:7]).as_matrix()*rows[:,None,7:]
    out[:,:3,3]=rows[:,:3];return out
def components(local):
    out=local.copy()
    for i,p in enumerate(PI):
        if p>=0:out[i]=out[p]@local[i]
    return out
R=matrices(D['meshes']['svd']['component']); RI=np.linalg.inv(R)
VR=matrices(D['meshes']['svch']['component']); VRI=np.linalg.inv(VR)
ROOT=N.index('WPN_root')
IDLE=components(matrices(D['clips']['idle']['frames'][0]))
TO_BIND=VR[ROOT]@np.linalg.inv(IDLE[ROOT])
VM=json.load(gzip.open(SRC/'Donor/vm.json.gz','rt',encoding='utf-8'))
V=np.asarray(VM['positions']).reshape(-1,3)
T=np.asarray(VM['triangles']).reshape(-1,3)
BN=VM['bone_names']; W=np.zeros((len(V),len(N)))
for i,row in enumerate(VM['weights']):
    for b,w in row:
        if BN[b] in N:W[i,N.index(BN[b])]=w
W/=np.maximum(W.sum(1,keepdims=True),1e-12)
def skin(pose,indices):
    p=np.column_stack((V[indices],np.ones(len(indices))))
    transforms=TO_BIND@pose@RI
    out=np.zeros((len(indices),3))
    for bi in np.where(W[indices].max(0)>0)[0]:
        out+=W[indices,bi,None]*(p@transforms[bi].T)[:,:3]
    return out
X=skin(IDLE,np.arange(len(V)))
def hand_indices(side):
    bones=[i for i,n in enumerate(N) if n.endswith('_'+side) and n.startswith(('hand_','thumb','index','middle','ring','pinky'))]
    return np.where(W[:,bones].sum(1)>.96)[0]
def apply_rigid(points,shift,rot,pivot):
    return (points-pivot)@Rotation.from_rotvec(rot).as_matrix().T+pivot+shift
