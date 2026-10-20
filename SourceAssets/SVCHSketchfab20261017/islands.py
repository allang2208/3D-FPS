import json, struct
import numpy as np
from collections import defaultdict
p = r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\download\svch.glb"
src=open(p,'rb').read(); _,_,length=struct.unpack_from('<III',src,0)
off=12; chunks=[]
while off<length:
    clen,ctype=struct.unpack_from('<II',src,off); chunks.append((ctype,off+8,clen)); off+=8+clen
j=json.loads(src[chunks[0][1]:chunks[0][1]+chunks[0][2]].decode('utf-8'))
BIN=src[chunks[1][1]:chunks[1][1]+chunks[1][2]]
CT={5120:('i1',1),5121:('u1',1),5122:('i2',2),5123:('u2',2),5125:('u4',4),5126:('f4',4)}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def acc(i):
    a=j['accessors'][i]; bv=j['bufferViews'][a['bufferView']]
    dt,sz=CT[a['componentType']]; n=NC[a['type']]
    st=bv.get('byteOffset',0)+a.get('byteOffset',0); stride=bv.get('byteStride') or sz*n; cnt=a['count']
    if stride==sz*n: return np.frombuffer(BIN,dtype=np.dtype(dt),count=cnt*n,offset=st).reshape(cnt,n)
    return np.array([np.frombuffer(BIN,dtype=np.dtype(dt),count=n,offset=st+i*stride) for i in range(cnt)])
nodes=j['nodes']; skin=j['skins'][0]; joints=skin['joints']
jname={k:nodes[joints[k]].get('name') for k in range(len(joints))}
mats=[m['name'] for m in j['materials']]
# Merge all meshes into one vertex/tri soup keyed by rounded position so islands are topological.
V=[];Tn=[];Mat=[];Dom=[]
base=0
for mi,m in enumerate(j['meshes']):
    pr=m['primitives'][0]
    pos=acc(pr['attributes']['POSITION']).astype(np.float64)
    jt=acc(pr['attributes']['JOINTS_0']).astype(np.int64)
    wt=acc(pr['attributes']['WEIGHTS_0']).astype(np.float64)
    idx=acc(pr['indices']).ravel().astype(np.int64).reshape(-1,3)
    dom=jt[np.arange(len(jt)),np.argmax(wt,axis=1)]
    V.append(pos); Tn.append(idx+base); Mat.append(np.full(len(idx),pr['material'])); Dom.append(dom)
    base+=len(pos)
V=np.vstack(V); T=np.vstack(Tn); Mat=np.concatenate(Mat); Dom=np.concatenate(Dom)
key={}
weld=np.zeros(len(V),dtype=np.int64)
for i,v in enumerate(V):
    k=tuple(np.round(v,5))
    if k not in key: key[k]=len(key)
    weld[i]=key[k]
nw=len(key)
TN=np.array([[weld[a],weld[b],weld[c]] for a,b,c in T])
parent=list(range(nw))
def find(a):
    while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
    return a
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[ra]=rb
for a,b,c in T:
    union(weld[a],weld[b]); union(weld[a],weld[c])
isl=defaultdict(list)
for ti,(a,b,c) in enumerate(T):
    isl[find(weld[a])].append(ti)
print(f"verts={len(V)} welded={nw} tris={len(T)} islands={len(isl)}")
rows=[]
for root,tris in isl.items():
    tris=np.array(tris)
    vi=np.unique(T[tris].ravel())
    P=V[vi]
    mn=P.min(0); mx=P.max(0)
    ms=set(mats[k] for k in np.unique(Mat[tris]))
    js=sorted(set(jname[int(d)] for d in np.unique(Dom[vi])))
    rows.append(dict(tris=len(tris), verts=len(vi), mat=sorted(ms), joints=js,
                     min=[round(float(v),2) for v in mn], max=[round(float(v),2) for v in mx],
                     size=[round(float(mx[i]-mn[i]),2) for i in range(3)], center=[round(float((mx[i]+mn[i])/2),2) for i in range(3)]))
rows.sort(key=lambda r:-r['tris'])
json.dump(rows, open(r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\islands.json","w"), indent=1)
print(f"{'tris':>5} {'mats':40s} {'joints':24s} {'X':>16} {'Y':>16} {'Z':>12}")
for r in rows[:45]:
    print(f"{r['tris']:5d} {','.join(r['mat']):40s} {','.join(r['joints']):24s} "
          f"[{r['min'][0]:7.1f},{r['max'][0]:7.1f}] [{r['min'][1]:7.1f},{r['max'][1]:7.1f}] [{r['min'][2]:6.1f},{r['max'][2]:6.1f}]")
