import json,numpy as np
from pathlib import Path
from collections import Counter,defaultdict
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';R={}
for rev in ('Saiga12KSurface20261018','Saiga12KDetail20261018'):
 for key in ('gun','ext12'):
  d=json.loads((P/f'SourceAssets/{rev}/Authoring/{key}.json').read_text());p=np.array(d['positions']);t=np.array(d['triangles']);_,ix,inv=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);p=p[ix];t=inv[t];edges=Counter();mats={}
  for fi,tri in enumerate(t):
   for a,b in zip(tri,np.roll(tri,-1)):e=tuple(sorted((int(a),int(b))));edges[e]+=1;mats[e]=d['parts'][fi]
  boundary={e for e,n in edges.items() if n==1};links=defaultdict(list)
  for a,b in boundary:links[a].append(b);links[b].append(a)
  seen=set();rows=[]
  for a in links:
   if a in seen:continue
   stack=[a];vs=[];seen.add(a)
   while stack:
    n=stack.pop();vs.append(n)
    for b in links[n]:
     if b not in seen:seen.add(b);stack.append(b)
   es=[e for e in boundary if e[0] in set(vs)];q=p[vs];rows.append({'points':len(vs),'parts':dict(Counter(mats[e] for e in es)),'perimeter_cm':sum(float(np.linalg.norm(p[a]-p[b])) for a,b in es),'bounds_cm':[q.min(0).tolist(),q.max(0).tolist()]})
  R[rev+'/'+key]={'boundary':len(boundary),'nonmanifold':sum(n>2 for n in edges.values()),'loops':rows}
(O/'Reports/boundary-loops.json').write_text(json.dumps(R,indent=2));print({k:{'boundary':v['boundary'],'nonmanifold':v['nonmanifold'],'large_loops':[x for x in v['loops'] if x['perimeter_cm']>1. and not ('LaserMark' in x['parts'])]} for k,v in R.items()})
