import sys,json,math,itertools,bpy
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O))
from pose_geometry import *
rig,D,prof,meta=load();p=source_pose(rig,D,prof);set_pose(rig,p)
ra=rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment']);root=p['WPN_root']@rig.data.bones['WPN_root'].matrix_local.inverted()@ra
ob=next(o for o in bpy.data.objects if o.type=='MESH');ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());skin=ev.to_mesh()
handgroups={g.index:g.name for g in ob.vertex_groups if g.name.startswith(('hand','thumb','index','middle','ring','pinky'))}
pts=[]
for v in ob.data.vertices:
 ww=[g for g in v.groups if g.group in handgroups and g.weight>.6]
 if ww and v.index%3==0:pts.append((handgroups[max(ww,key=lambda g:g.weight).group],root.inverted()@ob.matrix_world@skin.vertices[v.index].co))
parts=json.loads((B/'canonical_parts.json').read_text());grip=next(x for x in parts if x['name']=='9_l');bvh=BVHTree.FromPolygons([Vector(v) for v in grip['verts']],grip['faces'])
direction=Vector((.371,.691,.591)).normalized()
def depth(pt):
 if not (-.016<pt.x<.016 and .097<pt.y<.179 and -.08<pt.z<.029):return 0.
 origin=pt+direction*1e-7;count=0
 for i in range(8):
  hit,_,_,_=bvh.ray_cast(origin,direction,.3)
  if hit is None:break
  count+=1;origin=hit+direction*1e-6
 return bvh.find_nearest(pt)[3] if count%2 else 0.
results=[]
for y,z,ang in itertools.product((.012,.018,.024,.030),(-.012,-.006,0,.006),(-6,0,6)):
 m=Matrix.Translation((0,y,z))@Matrix.Translation((0,.086,.011))@Matrix.Rotation(math.radians(ang),4,'X')@Matrix.Translation((0,-.086,-.011));inv=m.inverted();groups={}
 for n,pt in pts:
  d=depth(inv@pt)*1000;groups.setdefault(n,[]).append(d)
 score=sum(sum(d*d for d in vv)/len(vv) for vv in groups.values())
 results.append(dict(y=y,z=z,angle=ang,score=score,groups={n:dict(max=max(vv),inside=sum(d>.5 for d in vv)) for n,vv in groups.items()}))
results.sort(key=lambda v:v['score']);(O/'registration_candidates.json').write_text(json.dumps(results,indent=2))
for row in results[:5]:print('REGISTRATION',row['y'],row['z'],row['angle'],row['score'],json.dumps({n:v for n,v in row['groups'].items() if v['max']>2}))
best=results[0];(O/'grip_registration.json').write_text(json.dumps(best,indent=2))
