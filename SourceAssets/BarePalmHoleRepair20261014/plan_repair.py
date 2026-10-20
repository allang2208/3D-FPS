"""Plan only small palm defects, preserving all existing non-patch vertices."""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from analyze_surface import analyze
R=Path(__file__).resolve().parent
B=R.parent/'ModularOutfit20260925/BarePalmV7'
OLD=json.loads((B/'M4_original.before_holes.json').read_text())
OLD_PATCHES=json.loads((B/'surface_repair.json').read_text())['patches']
def uv_key(uv):return np.array(sorted(uv)).reshape(-1)
OLD_UVS=np.array([uv_key(OLD['uv'][ti]) for p in OLD_PATCHES for ti in p['removed_faces']])
def triangulate_for_patch(d,patch):
 from triangulate_patch import triangulate
 ps=[d['positions'][d['triangles'][c['triangle']][c['a']]] for c in patch['corners']]
 ns=[d['normals'][c['triangle']][c['a']] for c in patch['corners']]
 try:return triangulate(ps,ns)
 except RuntimeError:
  cps=[];cns=[]
  for c in patch['corners']:
   vi=d['triangles'][c['triangle']][c['a']];ws=d['weights'][vi];side=1 if sum(w for n,w in ws.items() if n.endswith('_r'))>.5 else -1
   candidates=[(OLD['uv'][ti][ci],OLD['positions'][v],OLD['normals'][ti][ci]) for ti,tri in enumerate(OLD['triangles'])
    if OLD['triangle_materials'][ti]==2 for ci,v in enumerate(tri) if OLD['positions'][v][0]*side>0]
   distances=np.linalg.norm(np.array([row[0] for row in candidates])-d['uv'][c['triangle']][c['a']],axis=1);j=int(np.argmin(distances))
   if distances[j]>.0001:raise RuntimeError('Canonical palm correspondence missing')
   cps.append(candidates[j][1]);cns.append(candidates[j][2])
  return triangulate(cps,cns)
def palm_weight(ws):return sum(w for n,w in ws.items() if n.startswith('hand_') or '_metacarpal_' in n)
def make_plan(d):
 report=analyze(d)
 if not report['skin_triangles']:return [],report
 v=np.array(d['positions']);t=np.array(d['triangles'],dtype=int);m=d['triangle_materials']
 lookup={};wm=[]
 for vi,p in enumerate(v):wm.append(lookup.setdefault(tuple(np.round(p,4)),vi))
 ts=np.array([[wm[i] for i in face] for face in t]);seed_faces=set()
 for c in report['boundary_components']:
  if max(c['span'])<.5 and np.mean([palm_weight(d['weights'][vi]) for vi in c['vertices']])>.65:
   seed_faces.update(row[0] for row in c['edges'])
 for ti in report['flipped']:
  # Only the known inherited palm defects; anatomical bends elsewhere are not holes.
  dist=np.linalg.norm(OLD_UVS-uv_key(d['uv'][ti]),axis=1).min()
  if dist<.00002:seed_faces.add(ti)
 seeds={vi for ti in seed_faces for vi in ts[ti]}
 mats={m[ti] for ti in seed_faces}
 patch={ti for ti,f in enumerate(ts) if m[ti] in mats and any(vi in seeds for vi in f)}
 vf=defaultdict(set)
 for ti in patch:
  for vi in ts[ti]:vf[int(vi)].add(ti)
 remaining=set(patch);plans=[]
 while remaining:
  a=remaining.pop();group={a};todo=[a]
  while todo:
   ti=todo.pop()
   for vi in ts[ti]:
    for tj in vf[int(vi)]&remaining:remaining.remove(tj);group.add(tj);todo.append(tj)
  edges=defaultdict(list)
  for ti in group:
   face=list(ts[ti])
   for a,b in zip(face,face[1:]+face[:1]):
    if a!=b:edges[tuple(sorted((int(a),int(b))))].append((ti,int(a),int(b)))
  be=[rows[0] for rows in edges.values() if len(rows)==1];adj=defaultdict(set)
  for ti,a,b in be:adj[a].add(b);adj[b].add(a)
  if any(len(x)!=2 for x in adj.values()):raise RuntimeError('Patch boundary branches: '+d.get('path','source'))
  unseen=set(adj);loops=[]
  while unseen:
   start=min(unseen);loop=[];prev=None;cur=start
   while cur in unseen:
    unseen.remove(cur);loop.append(cur);nxt=next(n for n in adj[cur] if n!=prev);prev,cur=cur,nxt
   loops.append(loop)
  loop=max(loops,key=lambda l:sum(np.linalg.norm(v[a]-v[b]) for a,b in zip(l,l[1:]+l[:1])))
  # Native pistol reference poses spread the same small canonical patch across
  # a bent palm; retain every perimeter position and its exact native weights.
  if np.ptp(v[loop],axis=0).max()>6 or len(group)>60:raise RuntimeError('Patch exceeds local palm region: '+d.get('path','source'))
  # Retain the winding of the original exterior edge, not an arbitrary fan normal.
  wanted={(a,b) for ti,a,b in be}
  if (loop[0],loop[1]) not in wanted:loop.reverse()
  corners=[]
  for a,b in zip(loop,loop[1:]+loop[:1]):
   ti=next(ti for ti,aa,bb in be if aa==a and bb==b)
   corners.append(dict(triangle=ti,a=int(list(ts[ti]).index(a)),b=int(list(ts[ti]).index(b))))
  center=v[loop].mean(0);weights=defaultdict(float)
  for vi in loop:
   for n,w in d['weights'][vi].items():weights[n]+=w/len(loop)
  weights=dict(sorted(weights.items(),key=lambda kv:kv[1],reverse=True)[:8]);total=sum(weights.values());weights={n:w/total for n,w in weights.items()}
  plans.append(dict(remove=sorted(group),loop=loop,corners=corners,center=center.tolist(),weights=weights,material=m[min(group)]))
 return plans,report
if __name__=='__main__':
 all_plans=[];summary=[]
 for file in sorted((R/'Snapshots').glob('*.json')):
  d=json.loads(file.read_text());plans,report=make_plan(d)
  summary.append(dict(path=d['path'],skin_triangles=report['skin_triangles'],palm_patches=len(plans),
   small_palm_openings=int(sum(max(c['span'])<.5 and np.mean([palm_weight(d['weights'][vi]) for vi in c['vertices']])>.65 for c in report['boundary_components'])),
   seam_weight_splits=len(report['seam_weight_splits'])))
  if plans:
   all_plans.append(dict(path=d['path'],snapshot=str(file),source_sha256=d['source_sha256'],patches=plans))
   print('REPAIR',d['path'],len(plans),'patches',sum(len(p['remove']) for p in plans),'faces')
 (R/'repair_plan.json').write_text(json.dumps(all_plans,indent=2))
 (R/'scope_findings.json').write_text(json.dumps(summary,indent=2))
 print('SCANNED',len(summary),'AFFECTED',len(all_plans))
