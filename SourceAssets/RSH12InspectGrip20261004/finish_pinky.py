"""Small final MCP/IP rotational clearance using the exact grip triangles, not the SDF."""
import sys,json,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
rig,D,_,meta=load();profile=json.loads((O/'Single/profile.json').read_text());sample=D['clips']['inspect']['samples'][72]
base=pose(rig,D,profile,'inspect',sample);canon=canonical_pose(base,meta);skin=Skin(rig,'r');mask=np.char.startswith(skin.labels,'pinky')
skin.coords=skin.coords[mask];skin.weights=skin.weights[mask];skin.bound=skin.bound[:,mask];skin.labels=skin.labels[mask]
tree=grip_trees()[0][1];names=['pinky_01_r','pinky_02_r','pinky_03_r'];local={n:base[rig.data.bones[n].parent.name].inverted()@base[n] for n in names}
original=skin.points(base,canon);x=[0.]*9
def posed(x):
    p={n:m.copy() for n,m in base.items()}
    for i,n in enumerate(names):
        delta=Quaternion(Vector(x[i*3:i*3+3]).normalized(),math.radians(Vector(x[i*3:i*3+3]).length)) if any(x[i*3:i*3+3]) else Quaternion()
        t,q,s=local[n].decompose();p[n]=p[rig.data.bones[n].parent.name]@Matrix.LocRotScale(t,q@delta,s)
    return p
def cost(x):
    points=skin.points(posed(x),canon);ds=np.array([signed(tree,v) for v in points])*1000
    bad=np.minimum(ds-.18,0)
    return float(np.sum(bad*bad)*50+min(ds.min()-.18,0)**2*300+sum(v*v for v in x)*.03),ds
score,ds=cost(x)
for step in (1.5,.6,.2):
    for sweep in range(3):
        for i in range(9):
            for sign in (-1,1):
                candidate=x[:];candidate[i]+=step*sign
                if abs(candidate[i])>6.:continue
                new,dist=cost(candidate)
                if new<score:x,score,ds=candidate,new,dist
    print('PINKY_FINISH',step,round(max(0,-ds.min()),4),int((ds<0).sum()),flush=True)
p=posed(x);out={n:packed(p[rig.data.bones[n].parent.name].inverted()@p[n]) for n in names}
(O/'pinky_finish.json').write_text(json.dumps(dict(local_targets=out,rotation_degrees=x,penetration_max_mm=float(max(0,-ds.min()))),indent=2))
