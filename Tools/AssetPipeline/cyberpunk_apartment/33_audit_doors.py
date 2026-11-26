"""Check native door endpoint query and full authored sliding envelope against
the actual blocking environment triangles. No game or simulated interaction."""
import json
import numpy as np
from playable_config import ROOT, SCALE, COMPLEX

data=json.loads((ROOT/'geometry.json').read_text())['meshes']
geometry={n:np.asarray(m['positions'])[np.asarray(m['indices']).reshape(-1,3)]*SCALE
          for n,m in data.items() if n in COMPLEX}
doors=json.loads((ROOT/'authoring.json').read_text())['doors']

def intersects(tri, centre, half):
    t=tri-centre
    edges=[t[1]-t[0],t[2]-t[1],t[0]-t[2]]
    axes=[np.cross(edges[0],edges[1])]+[np.cross(e,a) for e in edges for a in np.eye(3)]
    for a in axes:
        if np.linalg.norm(a)<1e-7:continue
        p=t@a
        r=np.abs(a)@half
        if p.min()>r+1e-4 or p.max()<-r-1e-4:return False
    return True

report=[]
for d in doors:
    w,h=d['width_cm'],d['height_cm']
    along=0 if d['yaw']==90 else 1
    cross=1-along
    blockers=[]
    for side in (-1,1):
        c=np.array([d['x']*SCALE,d['y']*SCALE,.25+h/2])
        # Sweep the complete leaf from closed to opened, including its handles.
        c[along]+=side*(w/4+d['slide_cm']/2)
        half=np.array([0.,0.,h/2-2])
        half[along]=w/4+d['slide_cm']/2
        half[cross]=3.4
        for n,t in geometry.items():
            selected=t[np.all(t.max(1)>=c-half,axis=1)&np.all(t.min(1)<=c+half,axis=1)]
            if any(intersects(tri,c,half) for tri in selected):
                blockers.append(dict(side=side,mesh=n))
    report.append(dict(name=d['name'],clear=not blockers,blockers=blockers))
(ROOT/'door_clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
