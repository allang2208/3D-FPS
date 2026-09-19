from pathlib import Path
import numpy as np, trimesh, json
out=Path(__file__).resolve().parent
m=trimesh.load(out.parent/'seed_91379/textured_master_00001_.glb',force='mesh',process=False)
v, inv=np.unique(m.vertices,axis=0,return_inverse=True)
w=trimesh.Trimesh(vertices=v,faces=inv[m.faces],process=False)
edges, counts=np.unique(np.sort(w.edges,axis=1),axis=0,return_counts=True)
components=trimesh.graph.connected_components(edges,nodes=np.arange(len(v)),min_len=1)
labels=np.empty(len(v),dtype=np.int32)
for i,c in enumerate(components): labels[c]=i
fc=np.bincount(labels[w.faces[:,0]],minlength=len(components))
report={'exact_position_weld':{'vertices':len(v),'boundary_edges':int((counts==1).sum()),'more_than_two_faces_edges':int((counts>2).sum()),'duplicate_faces_ignoring_winding':int(len(w.faces)-len(np.unique(np.sort(w.faces,axis=1),axis=0))),'vertex_connected_components':len(components),'vertex_connected_component_face_counts_largest20':sorted(fc.tolist(),reverse=True)[:20]},'note':'Exact position welding avoids rounding-induced non-manifold counts. Vertex connectivity includes shared edges with more than two incident faces; surface adjacency splits at those edges.'}
(out/'topology_clarification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
