import bpy,numpy as np,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/SpiralPillarM14Meshy20261004/TeethRemeshV4'
inputs={'source':(P/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Authoring/M14_SupportSkin_v15.blend','M14_SoftDeathMesh'),
 'reduced':(P/'SourceAssets/AlienGeometry20261006/RemeshV3/SpiralPillarM14/SpiralPillarM14_RemeshV3.blend','M14_RemeshV3')}
report={}
for key,(file,name) in inputs.items():
 bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);o=bpy.data.objects[name];m=o.data
 p=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',p.ravel())
 f=np.empty((len(m.polygons),3),np.int32);m.loops.foreach_get('vertex_index',f.ravel())
 mat=np.empty(len(f),np.int32);m.polygons.foreach_get('material_index',mat)
 mid=next(i for i,x in enumerate(m.materials) if 'Mouth' in x.name)
 v,inv=np.unique(np.round(p,6),axis=0,return_inverse=True);faces=inv[f[mat==mid]]
 edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]));edges,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True);edges=edges[counts==1]
 adjacency={}
 for a,b in edges:adjacency.setdefault(int(a),set()).add(int(b));adjacency.setdefault(int(b),set()).add(int(a))
 components=[];unseen=set(adjacency)
 while unseen:
  seed=next(iter(unseen));stack=[seed];group=[];unseen.remove(seed)
  while stack:
   i=stack.pop();group.append(i)
   for j in adjacency[i]:
    if j in unseen:unseen.remove(j);stack.append(j)
  q=v[group];components.append(dict(count=len(group),center=q.mean(0).tolist(),bounds=np.ptp(q,axis=0).tolist(),non_ring_vertices=sum(len(adjacency[i])!=2 for i in group)))
 report[key]=dict(mouth_faces=len(faces),boundary_edges=len(edges),boundaries=sorted(components,key=lambda x:-x['count']))
(OUT/'boundaries.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
