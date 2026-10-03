import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
raw={p['name']:p for p in json.loads((B/'canonical_parts.json').read_text())}
p=raw['6_l'];verts=np.array(p['verts']);ids={i for i,v in enumerate(verts) if .0945<v[1]<.0955}
keys={i:tuple(round(x,6) for x in verts[i]) for i in ids};adj={k:set() for k in keys.values()}
for f in p['faces']:
 for a,b in zip(f,f[1:]+f[:1]):
  if a in ids and b in ids:adj[keys[a]].add(keys[b]);adj[keys[b]].add(keys[a])
def circle(v):
 x=v[:,0];z=v[:,2];c=np.linalg.lstsq(np.column_stack([2*x,2*z,np.ones(len(x))]),x*x+z*z,rcond=None)[0]
 return [float(c[0]),float(c[1]),float(math.sqrt(c[2]+c[0]**2+c[1]**2))]
seen=set();rings=[]
for k in adj:
 if k in seen:continue
 stack=[k];seen.add(k);vv=[]
 while stack:
  j=stack.pop();vv.append(j)
  for n in adj[j]:
   if n not in seen:seen.add(n);stack.append(n)
 if len(vv)>=10:rings.append(dict(center_xz_radius=circle(np.array(vv)),points=vv))
ring=circle(np.array([[r['center_xz_radius'][0],0,r['center_xz_radius'][1]] for r in rings]))
rings.sort(key=lambda r:(math.atan2(r['center_xz_radius'][1]-ring[1],r['center_xz_radius'][0]-ring[0])+math.pi/2+1e-4)%math.tau)
for r in rings:
 x,z,rr=r['center_xz_radius'];r['facet_phase']=math.atan2(r['points'][0][2]-z,r['points'][0][0]-x)%(math.pi/6)
rear=float(verts[:,1].max());front=float(verts[:,1].min());middle=(rear+front)/2
contract=dict(chambers=rings,cylinder_axis_xz_radius=ring,rear_plane_m=rear,front_plane_m=front,cylinder_middle_m=middle)
bpy.ops.wm.open_mainfile(filepath=str(B/'RSH12_Original.blend'))
axes=Matrix(((0,0,1,0),(1,0,0,0),(0,1,0,0),(0,0,0,1)));cm=Matrix.Diagonal((.001,.001,.001,1))@axes
vv=np.array([list(cm@v.co) for v in bpy.data.objects['10_l'].data.vertices])
center=(vv.min(axis=0)+vv.max(axis=0))/2;vv[:,0]-=center[0];vv[:,2]-=center[2]
levels={}
for v in vv:levels.setdefault(round(float(v[1]),6),[]).append(list(v))
contract['cartridge_sections']=[dict(y=y,radius=max(math.hypot(v[0],v[2]) for v in vlist),vertices=len(vlist)) for y,vlist in sorted(levels.items())]
contract['cartridge_bounds_m']=[list(vv.min(axis=0)),list(vv.max(axis=0))]
rim=[v for v in vv if abs(v[1]-.035900)<2e-6 and math.hypot(v[0],v[2])>.006]
contract['cartridge_rim_y_m']=float(np.mean([v[1] for v in rim]))
contract['cartridge_facet_phase']=math.atan2(rim[0][2],rim[0][0])%(math.pi/6)
(O/'fit_contract.json').write_text(json.dumps(contract,indent=2))
print(json.dumps({k:v for k,v in contract.items() if k!='chambers'},indent=2))
print('CHAMBERS',[(r['center_xz_radius'],len(r['points'])) for r in rings])
