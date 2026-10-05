"""Resolve source-material cuts that leave small chain patches moving separately."""
from pathlib import Path
import numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV13/Records';OUT.mkdir(parents=True,exist_ok=True)
d=np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
c=np.load(ROOT/'ProductionV11/Records/hardware_components.npz')
p,f,metal=d['p'],d['f'],d['metal'];weld=c['weld'];tri=weld[f]
graph=coo_matrix((np.ones(len(tri)*3,np.uint8),(tri.ravel(),tri[:,[1,2,0]].ravel())),
    shape=(int(weld.max())+1,)*2).tocsr()
count,labels=connected_components(graph,directed=False)
face_component=labels[tri[:,0]];size=np.bincount(face_component,minlength=count)
metal_size=np.bincount(face_component[metal],minlength=count)
summary=[]
for i in np.flatnonzero(metal_size):
    verts=np.unique(f[face_component==i]);points=p[verts]
    summary.append({'component':int(i),'triangles':int(size[i]),'metal_triangles':int(metal_size[i]),
        'min':points.min(0).tolist(),'max':points.max(0).tolist()})
np.savez(OUT/'full_connectivity.npz',vertex_components=labels[weld],face_components=face_component)
(OUT/'hardware_regions.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
mf=f[metal];fc=c['metal_face_components'];sizes=c['component_sizes']
major=np.flatnonzero(sizes>=1000)
major_vertex=[];major_owner=[]
for cid in major:
    ids=np.unique(mf[fc==cid]);major_vertex.extend(ids);major_owner.extend([cid]*len(ids))
major_vertex=np.array(major_vertex);major_owner=np.array(major_owner)
tree=cKDTree(p[major_vertex]);owner=np.full(len(p),-1,np.int32)
merged=[]
for cid in range(len(sizes)):
    ids=np.unique(mf[fc==cid]);parent=cid
    if cid not in major:
        _,nearest=tree.query(p[ids]);votes=np.bincount(major_owner[nearest],minlength=len(sizes));parent=int(votes.argmax())
        merged.append({'patch':cid,'parent':parent,'vertices':len(ids)})
    owner[ids]=parent
# The nameplate's paint/letters are one physical object, irrespective of metal mask.
plate_component=next(s['component'] for s in summary if s['triangles']==28230)
plate_vertices=np.flatnonzero(labels[weld]==plate_component);owner[plate_vertices]=53
seed=np.flatnonzero(owner>=0);tree=cKDTree(p[seed]);distance,nearest=tree.query(p)
nearest_owner=owner[seed[nearest]]
blend=1-np.clip(distance/.06,0,1)**2*(3-2*np.clip(distance/.06,0,1))
blend[owner>=0]=1
owner=np.where(owner>=0,owner,nearest_owner).astype(np.int32)
# Every coincident seam copy uses one owner/blend value across material slots.
_,first=np.unique(weld,return_index=True);owner=owner[first][weld];blend=blend[first][weld]
np.savez(OUT/'hardware_binding.npz',owner=owner,blend=blend.astype(np.float32),major=major)
(OUT/'hardware_patch_groups.json').write_text(json.dumps(merged,indent=2),encoding='utf8')
print(json.dumps({'geometry_components':count,'metal_bearing_components':len(summary),
    'rigid_regions':len(major),'small_patches_grouped':len(merged),'transition_vertices':int(((blend>0)&(blend<1)).sum())},indent=2))
