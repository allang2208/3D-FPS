import bpy,bmesh,sys,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
h,raw,p,t,m,uv,n,b=G.body()
for slot in ['M_A762_Bolt','M_A762_Trigger']:
 s=m==h['slots'].index(slot)
 if not s.any():continue
 print(slot,'bones',np.unique(b[t[s]],return_counts=True),'bounds',p[t[s]].min((0,1)),p[t[s]].max((0,1)),flush=True)
for key,cut in [('Body',-.018),('balanced_reargrip',-.017),('stable_antislip_reargrip',-.028),('phantom_reargrip',-.012)]:
 if key=='Body':sh,sp,st,sm=h,p,t,m;sid=h['slots'].index('M_A762_FactoryRearGrip')
 else:sh,sp,st,sm,*_=G.read(key);sp=sp*G.FLIP;sid=sh['slots'].index('A762_'+key+'_0')
 sel=sm==sid;vi,inv=np.unique(st[sel],return_inverse=True)
 me=bpy.data.meshes.new(key);me.from_pydata(sp[vi].tolist(),[],inv.reshape(-1,3).tolist());me.update()
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,cut),plane_no=(0,0,1),clear_outer=True)
 bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.z-cut)<1e-6],dist=1e-7)
 edge=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-6 for v in e.verts)]
 todo=set(edge);loops=[]
 while todo:
  cur=[todo.pop()];stack=cur.copy()
  while stack:
   e=stack.pop()
   for v in e.verts:
    for e2 in v.link_edges:
     if e2 in todo:todo.remove(e2);cur.append(e2);stack.append(e2)
  verts=set(v for e in cur for v in e.verts);closed=all(sum(e in cur for e in v.link_edges)==2 for v in verts)
  co=np.array([tuple(v.co) for v in verts]);loops.append({'edges':len(cur),'closed':closed,'bounds':[co.min(0).tolist(),co.max(0).tolist()]})
 print(key,json.dumps(sorted(loops,key=lambda v:-v['edges'])[:10]),flush=True)
