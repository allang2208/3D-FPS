import json,numpy as np
from pathlib import Path
from collections import Counter,defaultdict
O=Path(__file__).parent;d=json.loads((O/'inputs.json').read_text());W=np.array(d['rig_world']);skin=d['skin'];v=np.array(skin['vertices'])
look={};ids=[]
for i,p in enumerate(v):
 key=tuple(np.round(p,6));ids.append(look.setdefault(key,i))
edges=Counter(tuple(sorted((ids[p[i]],ids[p[(i+1)%len(p)]]))) for p in skin['faces'] for i in range(len(p)) if ids[p[i]]!=ids[p[(i+1)%len(p)]])
adj=defaultdict(set)
for (i,j),count in edges.items():
 if count==1:adj[i].add(j);adj[j].add(i)
todo=set(adj);rings=[]
while todo:
 group={todo.pop()};queue=list(group)
 while queue:
  for j in adj[queue.pop()]:
   if j in todo:todo.remove(j);group.add(j);queue.append(j)
 names=Counter()
 for i in group:
  for n,w in skin['weights'][i].items():names[n]+=w/len(group)
 rings.append({'vertices':sorted(group),'weights':dict(names)})
skin['boundaries']=rings;(O/'inputs.json').write_text(json.dumps(d))
print('RIG_WORLD',W.tolist());print('WELDED_RINGS',[(len(x['vertices']),x['weights']) for x in rings])
for f in [268,288,310,330,344,360,396,432]:
 p={n:np.array(m) for n,m in d['poses'][f].items()};inv=np.linalg.inv(p['WPN_root'])
 print('FRAME',f,'WORLD',{n:(W@p[n])[:3,3].round(4).tolist() for n in ['clavicle_r','upperarm_r','lowerarm_r','hand_r']})
 if f==330:print('CONTACT_ROOT',{n:(inv@p[n])[:3,3].round(4).tolist() for n in ['hand_r','index_01_r','index_02_r','index_03_r','middle_01_r','middle_02_r','middle_03_r','thumb_01_r','thumb_02_r','thumb_03_r']})
