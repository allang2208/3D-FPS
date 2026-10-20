import json
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
R=Path(__file__).resolve().parent
def analyze(d):
 v=np.array(d['positions']);t=np.array(d['triangles'],dtype=int);m=np.array(d['triangle_materials']);n=np.array(d['normals'])
 if not len(t):return dict(path=d['path'],skin_triangles=0,boundary_components=[],flipped=[],seam_weight_splits=[])
 if 'path' in d:
  skin={i for i,s in enumerate(d['materials']) if 'Bare' in s['path'] or 'Thumb' in s['path'] or 'Skin_' in s['slot']}
 else:skin={0,1,2}
 ids=np.where(np.isin(m,list(skin)))[0]
 lookup={};wm=list(range(len(v)));groups=defaultdict(list)
 for vi in np.unique(t[ids]):
  k=tuple(np.round(v[vi],4));wm[vi]=lookup.setdefault(k,int(vi));groups[wm[vi]].append(int(vi))
 e=defaultdict(list)
 for ti in ids:
  f=[wm[x] for x in t[ti]]
  for a,b in zip(f,f[1:]+f[:1]):
   if a!=b:e[tuple(sorted((a,b)))].append((int(ti),a,b))
 edges=[r[0] for r in e.values() if len(r)==1]
 adj=defaultdict(set)
 for ti,a,b in edges:adj[a].add(b);adj[b].add(a)
 remaining=set(adj);components=[]
 while remaining:
  seed=remaining.pop();group={seed};todo=[seed]
  while todo:
   a=todo.pop()
   for b in adj[a]&remaining:remaining.remove(b);group.add(b);todo.append(b)
  g=sorted(group);ps=v[g];ws=Counter()
  for vi in g:ws.update(d['weights'][vi])
  components.append(dict(vertices=g,center=ps.mean(0).tolist(),span=np.ptp(ps,axis=0).tolist(),
   bone_weights=ws.most_common(3),edges=[r for r in edges if r[1] in group],branched=any(len(adj[a])!=2 for a in group)))
 cr=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]])
 sign=np.einsum('ij,ij->i',cr,n.mean(1));orientation=np.sign(np.median(sign[ids]))
 flipped=[int(i) for i in ids if sign[i]*orientation < -1e-8]
 seams=[]
 for vi,gg in groups.items():
  if len(gg)<2:continue
  ws=[d['weights'][g] for g in gg];names=set().union(*ws)
  diff=max(sum(abs(a.get(k,0)-b.get(k,0)) for k in names) for a in ws for b in ws)
  if diff>.001:seams.append(dict(vertices=gg,position=v[vi].tolist(),weight_difference=diff,weights=ws))
 return dict(path=d.get('path','master'),skin_triangles=len(ids),boundary_components=components,flipped=flipped,seam_weight_splits=seams)
if __name__=='__main__':
 reports=[]
 for f in (R/'Snapshots').glob('*.json'):
  d=json.loads(f.read_text());r=analyze(d);r['snapshot']=str(f);reports.append(r)
  print(d['path'],'triangles',r['skin_triangles'],'loops',len(r['boundary_components']),'flipped',len(r['flipped']),'weight_splits',len(r['seam_weight_splits']))
  for c in r['boundary_components']:print(' LOOP',len(c['vertices']),np.round(c['center'],3),np.round(c['span'],3),c['bone_weights'],c['branched'])
  for i in r['flipped'][:10]:print(' FLIP',i,np.mean(np.array(d['positions'])[d['triangles'][i]],0))
 (R/'diagnosis.json').write_text(json.dumps(reports,indent=2))
