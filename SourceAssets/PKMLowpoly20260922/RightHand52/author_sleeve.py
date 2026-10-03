from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
P=Path(__file__).resolve().parent;b=json.loads((P/'Authored/BarePalmV7.json').read_text());d=json.loads((P/'Inputs/FittedSleevesV1_source.json').read_text());bones=json.loads((P/'Inputs/bare.json').read_text())['bones'];v=[Vector(p) for p in b['positions']];e=Vector(bones['lowerarm_r']['p']);axis=Vector(bones['hand_r']['p'])-e;length=axis.length;axis.normalize();belongs=[sum(w for n,w in ws.items() if n.endswith('_r'))>.99 for ws in b['weights']];faces=[f for f in b['triangles'] if all(belongs[i] for i in f) and sum((v[i]-e).dot(axis)/length for i in f)/3<1.02];tree=BVHTree.FromPolygons(v,faces,all_triangles=True)
for i,old in enumerate(d['weights']):
 if sum(w for n,w in old.items() if n.endswith('_r'))<.99:continue
 point=Vector(d['positions'][i]);station=(point-e).dot(axis)/length
 if station<-.15:continue
 hit,_,fi,_=tree.find_nearest(point);f=faces[fi];factors=barycentric_transform(hit,*[v[j] for j in f],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));target={}
 for vi,fac in zip(f,factors):
  for n,w in b['weights'][vi].items():target[n]=target.get(n,0)+max(0,float(fac))*w
 total=sum(target.values());target={n:w/total for n,w in target.items()};a=max(0,min(1,(station+.15)/.2));a=a*a*(3-2*a);new={n:(1-a)*old.get(n,0)+a*target.get(n,0) for n in set(old)|set(target)};total=sum(new.values());d['weights'][i]={n:w/total for n,w in new.items() if w>1e-9}
d['right_hand_revision']='RightHand52';d['bare_authored_sha256']=hashlib.sha256((P/'Authored/BarePalmV7.json').read_bytes()).hexdigest();(P/'Authored/FittedSleevesV1.json').write_text(json.dumps(d,separators=(',',':')));print('SLEEVE_AUTHORED')
