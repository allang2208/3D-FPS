import json, struct
import numpy as np
from collections import defaultdict
np.set_printoptions(suppress=True)
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
print("JOINTS:", {k:v for k,v in jname.items()})
print()
grid=defaultdict(lambda:[np.array([1e9]*3),np.array([-1e9]*3),0])
allfaces=[]
for mi,m in enumerate(j['meshes']):
    pr=m['primitives'][0]
    pos=acc(pr['attributes']['POSITION']).astype(np.float64)
    jt=acc(pr['attributes']['JOINTS_0']).astype(np.int64)
    wt=acc(pr['attributes']['WEIGHTS_0']).astype(np.float64)
    idx=acc(pr['indices']).ravel().astype(np.int64)
    mat=mats[pr['material']]
    dom=jt[np.arange(len(jt)),np.argmax(wt,axis=1)]
    for d in np.unique(dom):
        sel=dom==d; P=pos[sel]; nm=jname[d]
        a=grid[(mat,nm)]
        a[0]=np.minimum(a[0],P.min(0)); a[1]=np.maximum(a[1],P.max(0)); a[2]+=len(P)
    allfaces.append((mat,pos,idx))
print(f"{'material':14s} {'joint':14s} {'n':>5s}  X[min,max]        Y[min,max]       Z[min,max]")
for (mat,nm),(mn,mx,c) in sorted(grid.items()):
    print(f"{mat:14s} {nm:14s} {c:5d}  [{mn[0]:7.2f},{mx[0]:7.2f}] [{mn[1]:7.2f},{mx[1]:7.2f}] [{mn[2]:7.2f},{mx[2]:7.2f}]")
