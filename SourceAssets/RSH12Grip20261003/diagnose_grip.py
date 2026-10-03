import sys,json,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from pose_geometry import *
from mathutils.bvhtree import BVHTree
out={}
revision='after' if '--' in sys.argv and sys.argv[sys.argv.index('--')+1]=='after' else 'before'
for kind in ('idle','aim'):
 rig,D,profile,meta=load()
 if revision=='after':profile=json.loads((B/'Single/profile.json').read_text())
 p=source_pose(rig,D,profile,kind);set_pose(rig,p)
 deps=bpy.context.evaluated_depsgraph_get();ob=next(o for o in bpy.data.objects if o.type=='MESH');ev=ob.evaluated_get(deps);mesh=ev.to_mesh();verts=[ob.matrix_world@v.co for v in mesh.vertices]
 gun_faces=[list(poly.vertices) for poly in mesh.polygons if 'Manny' not in ob.data.materials[poly.material_index].name]
 hand_bones={g.index:g.name for g in ob.vertex_groups if g.name.startswith(('thumb','index','middle','ring','pinky','hand'))}
 root=rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment']);canonical=(rig.matrix_world@p['WPN_root']@rig.data.bones['WPN_root'].matrix_local.inverted()@root).inverted()
 groups={}
 for v in ob.data.vertices:
  ww=[g for g in v.groups if g.group in hand_bones and g.weight>.5]
  if not ww:continue
  n=hand_bones[max(ww,key=lambda g:g.weight).group];groups.setdefault(n,[]).append(canonical@verts[v.index])
 out[kind]={n:dict(min=[min(v[a] for v in vv) for a in range(3)],max=[max(v[a] for v in vv) for a in range(3)]) for n,vv in groups.items()}
 bvh=BVHTree.FromPolygons(verts,gun_faces,all_triangles=False);inside={}
 for n in groups:inside[n]=[]
 for v in ob.data.vertices:
  ww=[g for g in v.groups if g.group in hand_bones and g.weight>.5]
  if not ww:continue
  name=hand_bones[max(ww,key=lambda g:g.weight).group];pt=verts[v.index];nearest,normal,idx,dist=bvh.find_nearest(pt)
  if nearest is None:continue
  # Use parity for closed gun surfaces; normal sign alone is ambiguous near edges.
  direction=Vector((.37,.69,.59)).normalized();origin=pt+direction*1e-7;hits=0
  for _ in range(40):
   hit,_,_,distance=bvh.ray_cast(origin,direction,2.)
   if hit is None:break
   hits+=1;origin=hit+direction*1e-6
  if hits%2:inside[name].append(dist*1000)
 out[kind]['penetration_mm']={n:dict(vertices=len(vv),max=max(vv,default=0)) for n,vv in inside.items()}
 ev.to_mesh_clear();render(rig,p,meta,revision+'_'+kind,'hip' if kind=='idle' else 'aim')
(O/('grip_'+revision+'.json')).write_text(json.dumps(out,indent=2))
for kind,data in out.items():print(kind,json.dumps(data['penetration_mm']))
