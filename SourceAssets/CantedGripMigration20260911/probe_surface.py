from pathlib import Path
O=Path(__file__).parent
s=(O/'refine_canted_surface.py').read_text();s=s[:s.index('for xyz in')];exec(compile(s,str(O/'probe_generated.py'),'exec'))
hit=BVHTree.FromPolygons(vertices,faces,all_triangles=True).overlap(tree)
from collections import defaultdict
groups=defaultdict(list)
for i,j in hit:
 c=sum((B.inverted()@vertices[k] for k in faces[i]),Vector())/3;groups[labels[faces[i][0]]].append(list(c))
print({k:{'count':len(v),'bbox':[[min(x[i] for x in v),max(x[i] for x in v)] for i in range(3)]} for k,v in groups.items()})
