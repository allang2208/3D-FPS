"""Tailor the charcoal short sleeve in native author space; closed inward hem."""
import json,sys,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterKnit20260929'
sys.path.insert(0,str(P/'Tools/ModularOutfit'));from chainmail_interlace_native import retarget

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'))+'\n',encoding='utf-8')
def tailor(data):
 names=sorted({n for w in data['weights'] for n in w});bm=bmesh.new();deform=bm.verts.layers.deform.verify();uv=bm.loops.layers.uv.verify()
 verts=[bm.verts.new(p) for p in data['positions']]
 for v,w in zip(verts,data['weights']):
  for n,x in w.items():v[deform][names.index(n)]=x
 for fi,f in enumerate(data['triangles']):
  face=bm.faces.new([verts[i] for i in f]);face.material_index=0
  for loop,coord in zip(face.loops,data['uv'][fi]):loop[uv].uv=coord
 # Only join coincident points near the new cut, never shoulder caps.
 for side in ['l','r']:
  shoulder=Vector(data['bones']['upperarm_'+side]['position']);elbow=Vector(data['bones']['lowerarm_'+side]['position']);axis=(elbow-shoulder).normalized();cut=(elbow-shoulder).length*.55
  def belongs(v):return sum(w for i,w in v[deform].items() if names[i].endswith('_'+side))>.5
  selected=[v for v in bm.verts if belongs(v)]
  bmesh.ops.remove_doubles(bm,verts=[v for v in selected if abs((v.co-shoulder).dot(axis)-cut)<3],dist=.00001)
  selected={v for v in bm.verts if belongs(v)}
  geom=list(selected)+[e for e in bm.edges if all(v in selected for v in e.verts)]+[f for f in bm.faces if all(v in selected for v in f.verts)]
  plane=shoulder+axis*cut
  bmesh.ops.bisect_plane(bm,geom=geom,dist=.00001,plane_co=plane,plane_no=axis,clear_outer=True,clear_inner=False)
  edges=[e for e in bm.edges if e.is_boundary and all(abs((v.co-plane).dot(axis))<.001 for v in e.verts)]
  if not edges:raise RuntimeError('No short sleeve boundary '+side)
  adjacency={}
  for e in edges:
   for v in e.verts:adjacency.setdefault(v,[]).append(e.other_vert(v))
  remaining=set(adjacency);rings=[]
  while remaining:
   start=next(iter(remaining));ring=[];v=start;prev=None
   while v not in ring:
    ring.append(v);remaining.discard(v)
    if len(adjacency[v])!=2:raise RuntimeError('Open cut boundary '+side)
    opts=[n for n in adjacency[v] if n!=prev];prev,v=v,opts[0]
   rings.append(ring)
  if len(rings)!=2:raise RuntimeError('Expected inner/outer cuff '+str([len(r) for r in rings]))
  center=sum((v.co for ring in rings for v in ring),Vector())/sum(map(len,rings))
  rings.sort(key=lambda ring:sum((v.co-center).length for v in ring)/len(ring),reverse=True);outer,inner=rings
  # Follow the existing shell cut; roll toward the arm, never bulge outside.
  rolled=[]
  for v in outer:
   radial=(v.co-center-axis*(v.co-center).dot(axis)).normalized();q=bm.verts.new(v.co+axis*.08-radial*.06)
   for i,w in v[deform].items():q[deform][i]=w
   rolled.append(q)
  for i,v in enumerate(outer):
   face=bm.faces.new([v,outer[(i+1)%len(outer)],rolled[(i+1)%len(outer)],rolled[i]]);face.material_index=1
  rolled_edges=[bm.edges.get((rolled[i],rolled[(i+1)%len(rolled)])) for i in range(len(rolled))]
  inner_edges=[bm.edges.get((inner[i],inner[(i+1)%len(inner)])) for i in range(len(inner))]
  result=bmesh.ops.bridge_loops(bm,edges=rolled_edges+inner_edges,use_pairs=True)
  for f in result['faces']:f.material_index=1
  for f in bm.faces:
   if f.material_index==1 and all(abs((v.co-plane).dot(axis))<.5 for v in f.verts):
    f.normal_update()
    if f.normal.dot(axis)>0:f.normal_flip()
    for loop in f.loops:
     q=loop.vert.co-center;loop[uv].uv=(math.atan2(q.y,q.x)/(2*math.pi),(loop.vert.co-shoulder).dot(axis)/25)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.verts.ensure_lookup_table();bm.verts.index_update()
 out=dict(data);out.update(positions=[list(v.co) for v in bm.verts],weights=[{names[i]:w for i,w in v[deform].items()} for v in bm.verts],
  triangles=[[v.index for v in f.verts] for f in bm.faces],uv=[[list(l[uv].uv) for l in f.loops] for f in bm.faces],
  normals=[[list(l.vert.normal) for l in f.loops] for f in bm.faces],triangle_materials=[f.material_index for f in bm.faces],contract='Charcoal cotton short sleeve; mid-upper-arm cut, existing inner shell and inward rolled hem; original native rig')
 # Existing upper body smoothing uses the same normal orientation as its source.
 original=np.asarray(data['positions']);tri=np.asarray(data['triangles']);cross=np.cross(original[tri[:,1]]-original[tri[:,0]],original[tri[:,2]]-original[tri[:,0]])
 if np.sum(cross*np.asarray(data['normals']).mean(1))<0:out['normals']=(-np.asarray(out['normals'])).tolist()
 bm.free();return out

master=tailor(read(R/'Authored/M4.json'));write(R/'ShortSleeve/M4.json',master)
for row in read(R/'manifest.json'):
 name=row['profile'];target=read(R/'Authored'/(name+'.json'))
 if name=='M4':result=master
 elif name=='Body':result=tailor(target)
 else:result,_=retarget(master,target)
 result['profile']=name;write(R/'ShortSleeve'/(name+'.json'),result)
print('SHORT_SLEEVES_AUTHORED',flush=True)
