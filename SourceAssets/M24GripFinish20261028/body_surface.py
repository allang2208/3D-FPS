"""Stock contact uses the union of closed connected shells, not an internal nearest face."""
body=next(p for p in surfaces if p['name']=='M24_base');T=body['tri'];lookup={};parent=list(range(len(T)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i,tri in enumerate(T):
 for p in tri:
  key=tuple(np.round(p,6))
  if key in lookup:parent[find(i)]=find(lookup[key])
  else:lookup[key]=i
groups={}
for i in range(len(T)):groups.setdefault(find(i),[]).append(i)
shells=[]
for indices in groups.values():
 tri=T[indices];v=tri.reshape((-1,3));faces=np.arange(len(v)).reshape((-1,3))
 if len(tri)<4:continue
 shells.append((BVHTree.FromPolygons(v.tolist(),faces.tolist(),all_triangles=True),v.min(0),v.max(0)))
print('BODY_SHELLS',len(shells),sorted([len(i) for i in groups.values()],reverse=True)[:10],flush=True)
old_actual=actual
def actual(row,P,full_winding=False,subset=None):
 ds=old_actual(row,P,full_winding,subset)
 if 'M24_base' not in ds or full_winding:return ds
 inv=np.array(rest[body['bone']]@row[body['bone']].inverted());Q=P@inv[:3,:3].T+inv[:3,3];d=np.full(len(P),.1)
 for bvh,lo,hi in shells:
  for i in np.where(np.all((Q>lo-.015)&(Q<hi+.015),axis=1))[0]:
   p,n,_,dist=bvh.find_nearest(Vector(Q[i]));value=dist if (Vector(Q[i])-p).dot(n)>=0 else -dist
   d[i]=min(d[i],value)
 ds['M24_base']=d;return ds
