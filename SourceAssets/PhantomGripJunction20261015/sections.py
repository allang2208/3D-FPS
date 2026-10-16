import numpy as np,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'PythonLibs'))
from scipy.spatial import cKDTree
O=Path(__file__).parent;W=O/'Working';S=O.parent;R={}
HK=np.array(json.loads((S/'HK416Reworked20260930/authoring.json').read_text())['root_matrix']);HKI=np.linalg.inv(HK)
CFG={'M4':(0,.007,.014),'M16':(1,.004,.011),'AKM':(0,-.004,.005),'QBZ191':(0,.010,.017),'PKM':(1,.007,.017),'HK416':(0,-.0003,.008),'A762':(1,-.0103,-.006),'Super90':(0,-.8361,-.829)}
def contour(p,t,z):
 q=p[t];segments=[]
 for a,b,c in q[(q[:,:,2].min(1)<z)&(q[:,:,2].max(1)>z)]:
  hits=[]
  for u,v in [(a,b),(b,c),(c,a)]:
   if (u[2]-z)*(v[2]-z)<0:hits.append(u+(v-u)*((z-u[2])/(v[2]-u[2])))
  if len(hits)==2 and np.linalg.norm(hits[0]-hits[1])>1e-9:segments.append(np.array(hits))
 pts=np.array(segments)[:,:,:2].reshape(-1,2);parent=np.arange(len(pts))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for a,b in cKDTree(pts).query_pairs(1e-6):parent[find(a)]=find(b)
 groups=np.array([find(i) for i in range(len(pts))]);adj={}
 for a,b in groups.reshape(-1,2):
  if a!=b:adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
 ends=[i for i,n in adj.items() if len(n)==1];gaps=[]
 if len(ends)>1:
  dist,idx=cKDTree(pts[ends]).query(pts[ends],k=2)
  gaps=dist[:,1].tolist()
  for j,i in enumerate(ends):
   other=ends[idx[j,1]]
   if dist[j,1]<.00015 and len(adj[i])==1 and len(adj[other])==1:adj[i].add(other);adj[other].add(i)
 order={v:sorted(ns,key=lambda w:np.arctan2(*(pts[w]-pts[v])[::-1])) for v,ns in adj.items()};seen=set();polys=[]
 for start,neighbors in order.items():
  for second in neighbors:
   if (start,second) in seen:continue
   a,b=start,second;loop=[]
   while (a,b) not in seen:
    seen.add((a,b));loop.append(a);ns=order[b];c=ns[(ns.index(a)-1)%len(ns)];a,b=b,c
   if (a,b)!=(start,second) or len(loop)<3 or len(set(loop))!=len(loop):continue
   q=pts[loop];area=np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))*.5
   if area>1e-10:polys.append((area,q.tolist()))
 polys.sort(reverse=True,key=lambda p:p[0])
 return {'segments':len(segments),'polygons':len(polys),'areas':[p[0] for p in polys[:6]],'outer':polys[0][1] if polys else [],'holes':0,'endpoint_gaps_mm':np.quantile(gaps,[0,.5,.9,1]).tolist() if gaps else [],'degree_counts':{str(d):sum(len(n)==d for n in adj.values()) for d in set(map(len,adj.values()))}}
for key,(slot,cut,high) in CFG.items():
 d=np.load(W/(key+'.npz'));gp=d['grip_positions'];gt=d['grip_triangles'];gm=d['grip_mids'];hp=d['host_positions'];ht=d['host_triangles'];hm=d['host_mids']
 if key=='HK416':gp=gp@HKI[:3,:3].T+HKI[:3,3];hp=hp@HKI[:3,:3].T+HKI[:3,3]
 use_current=key in ['HK416','A762','Super90'];nt=gt[gm!=slot] if use_current else ht[np.isin(hm,d['factory_slots'])];np_=gp if use_current else hp
 a=contour(gp,gt[gm==slot],cut);b=contour(np_,nt,high)
 R[key]={'body_slot':slot,'cut':cut,'high':high,'upper_source':'current' if use_current else 'factory','body':a,'native':b};print('SECTION',key,'body',a['segments'],a['polygons'],a['areas'][:3],'native',b['segments'],b['polygons'],b['areas'][:3],flush=True)
(O/'sections.json').write_text(json.dumps(R,indent=2))
