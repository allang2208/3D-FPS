"""Exact installed V9 coverage surface + the same corrective driver as runtime."""
from pathlib import Path
import sys,json,gzip,numpy as np
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'ForegripFit20261019'))
from arm_math import *
O=Path(__file__).resolve().parent
V9=O.parents[2]/'SourceAssets/BareSkinV9Rollout_20261017'
sys.path.insert(0,str(V9))
from jc import Driver

ref=matrices(arms['reference']);wref=matrices(weapon['reference'])
leader={n:{'t':m[:3,3].tolist(),'q':R.from_matrix(rigid(m)[:3,:3]).as_quat().tolist()} for n,m in zip(names,wref)}
coverage=json.load(gzip.open(O/'Inputs/coverage.json.gz','rt'))
driver=Driver(leader,coverage['morph_names'])
base=json.loads((V9/'Work/batch1/fd81da14598c.json').read_text())
shapes=dict(base['morphs'])
shapes.update(json.loads((V9/'Work/batch1_pose/fd81da14598c.json').read_text())['morphs'])
receipt=json.loads((V9/'Installed_pose2/fd81da14598c.json').read_text())
assert receipt['sha256']==coverage['sha256']
for key in receipt['emptied_stale_morphs']:shapes.pop(key,None)
shapes.update(json.loads((V9/'Work/batch1_pose2/fd81da14598c.json').read_text())['morphs'])
positions=np.array(coverage['positions']);deltas={}
for name,rows in shapes.items():
    if name not in coverage['morph_names']:continue
    ar=np.array(rows);delta=np.zeros_like(positions);vi=ar[:,0].astype(int)
    delta[vi]=ar[:,1:4]-positions[vi];deltas[name]=delta
glove=json.load(gzip.open(O/'Inputs/glove.json.gz','rt'))

def matrix_pose(p):return {n:(m[:3,3],R.from_matrix(rigid(m)[:3,:3]).as_quat()) for n,m in zip(names,p)}

def skinned(data,p,corrective=False):
    v=np.array(data['positions'])
    if corrective:
        for name,weight in driver.weights(matrix_pose(p)).items():
            if weight>=.001 and name in deltas:v+=deltas[name]*weight
    inv=np.linalg.inv(matrices(data['reference']));result=np.zeros_like(v)
    weights=np.zeros((len(v),len(names)))
    for i,row in enumerate(data['weights']):
        for b,w in row:weights[i,ids[data['weight_bones'][b]]]=w
    for j in np.flatnonzero(weights.max(0)>0):
        m=p[j]@inv[j];result+=(v@m[:3,:3].T+m[:3,3])*weights[:,j,None]
    return result
