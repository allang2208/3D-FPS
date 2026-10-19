import json,struct,collections
from pathlib import Path
import numpy as np
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12K20261017')
b=(O/'Original/saiga12k.glb').read_bytes(); n,t=struct.unpack_from('<II',b,12);j=json.loads(b[20:20+n]);buf=b[28+n:]
ct={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}; nc={'VEC3':3,'VEC4':4,'SCALAR':1,'MAT4':16}
def acc(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];d=np.dtype(ct[a['componentType']]);k=nc[a['type']];off=v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.ndarray((a['count'],k),d,buf,off,strides=(v.get('byteStride',d.itemsize*k),d.itemsize)).copy()
names=[j['nodes'][i]['name'] for i in j['skins'][0]['joints']]
P=[];N=[];T=[];B=[];M=[];offset=0
for mesh in j['meshes']:
 for p in mesh['primitives']:
  aa=p['attributes'];pos=acc(aa['POSITION']);ids=acc(p['indices']).reshape(-1,3);weights=acc(aa['WEIGHTS_0']);ji=acc(aa['JOINTS_0']);dom=ji[np.arange(len(pos)),weights.argmax(1)]
  P.extend(pos.tolist());N.extend(acc(aa['NORMAL']).tolist());T.extend((ids+offset).tolist());B.extend([names[int(x)] for x in dom]);M.extend([p['material']]*len(ids));offset+=len(pos)
data=dict(positions=P,normals=N,triangles=T,bones=B,materials=j['materials'],face_material=M)
(O/'Authoring/source_geometry.json').write_text(json.dumps(data),encoding='utf-8')
# Weld positions for semantic disconnected shells, retaining original vertex/face indices.
parent=list(range(len(P)));seen={}
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(a,b):parent[find(a)]=find(b)
for i,p in enumerate(P):
 key=tuple(round(v,4) for v in p)
 if key in seen:union(i,seen[key])
 else:seen[key]=i
for tri in T:
 for v in tri[1:]:union(tri[0],v)
groups=collections.defaultdict(list)
for i,tri in enumerate(T):groups[find(tri[0])].append(i)
islands=[];pa=np.array(P)
for ids in groups.values():
 vs=sorted({v for i in ids for v in T[i]});q=pa[vs];bb=collections.Counter(B[v] for v in vs)
 islands.append(dict(faces=ids,vertices=vs,count=len(ids),min=q.min(0).round(4).tolist(),max=q.max(0).round(4).tolist(),bone=bb.most_common(1)[0][0],materials=sorted({M[i] for i in ids})))
islands.sort(key=lambda x:-x['count'])
(O/'Authoring/source_islands.json').write_text(json.dumps(islands),encoding='utf-8')
print('SOURCE',len(P),len(T),'bounds',pa.min(0),pa.max(0),'islands',len(islands))
for i,x in enumerate(islands):
 if x['count']>=10:print(i,{k:v for k,v in x.items() if k not in ('faces','vertices')})
