"""Rebind the reduced surface to the accepted soft cage, offline only."""
from pathlib import Path
import json, sys, numpy as np
from scipy.spatial import cKDTree

ROOT=Path(sys.argv[2]) if len(sys.argv)>2 else Path('D:/FPS3D/FPSGAME/SourceAssets/AlienGeometry20261006/RemeshV3')
species=sys.argv[1];out=ROOT/species
with (out/'surface.bin').open('rb') as stream:
    count=int(np.fromfile(stream,dtype='<i4',count=1)[0]);points=np.fromfile(stream,dtype='<f4').reshape(count,3)
points=np.unique(points,axis=0).astype(np.float64)
cage=json.loads((out/'cage.json').read_text(encoding='utf8'))
nodes=np.asarray(cage['nodes'],float);tets=np.asarray(cage['tetrahedra'],np.int32);v=nodes[tets]
inverse=np.linalg.inv(np.transpose(v[:,1:]-v[:,:1],(0,2,1)))
tree=cKDTree(v.mean(1));indices=np.empty((len(points),4),np.int32);weights=np.empty((len(points),4),float)
clamped=0
for start in range(0,len(points),4096):
    p=points[start:start+4096];_,near=tree.query(p,k=min(48,len(tets)),workers=2)
    delta=p[:,None,:]-v[near,0];xyz=np.einsum('nkij,nkj->nki',inverse[near],delta)
    bary=np.concatenate((1-xyz.sum(2,keepdims=True),xyz),axis=2)
    penalty=np.minimum(bary,0)**2;cost=penalty.sum(2)
    chosen=cost.argmin(1);rows=np.arange(len(p));w=bary[rows,chosen]
    clamped+=int((w.min(1)<-1e-5).sum());w=np.maximum(w,0);w/=w.sum(1,keepdims=True)
    indices[start:start+len(p)]=tets[near[rows,chosen]];weights[start:start+len(p)]=w
records=np.column_stack((points,indices,weights,np.full(len(points),-1),np.zeros(len(points)))).astype('<f4')
with (out/'embedding.bin').open('wb') as stream:
    np.array(records.shape,dtype='<i4').tofile(stream);records.tofile(stream)
(out/'corpse_authoring.json').write_text(json.dumps(dict(complete=True,species=species,source_vertices=count,
    embedded_positions=len(points),nodes=len(nodes),tetrahedra=len(tets),nearest_boundary_bindings=clamped,
    reused_accepted_cage=True,tests_run=False),indent=2)+'\n',encoding='utf8')
print('REMESH_CORPSE_BOUND',species,len(points),len(nodes),clamped)
