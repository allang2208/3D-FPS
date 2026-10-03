"""Narrow offline skin/metal contact check for the requested cocking action."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils import Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;SA=O.parent/'RSH12SingleAction20261003';out=[]
for t in (0.,.06,.20,.25,.30,.45,.60,.70,.80,1.):
 bpy.ops.wm.open_mainfile(filepath=str(SA/'single/A_RSH12_aim_fire_Editable.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='POSE';bpy.context.scene.frame_set(round(t*120));bpy.context.view_layer.update()
 ob=next(o for o in bpy.data.objects if o.type=='MESH');ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();vv=[ob.matrix_world@v.co for v in mesh.vertices];groups={g.index:g.name for g in ob.vertex_groups}
 labels={v.index:max(v.groups,key=lambda g:g.weight).group for v in ob.data.vertices if v.groups}
 solids=[]
 for name in ('WPN_root','WPN_Hammer','WPN_Trigger','WPN_Cylinder'):
  faces=[list(poly.vertices) for poly in mesh.polygons if all(groups.get(labels.get(i))==name for i in poly.vertices)]
  ids={i for face in faces for i in face};points=[vv[i] for i in ids]
  if not points:continue
  lo=Vector(tuple(min(v[a] for v in points) for a in range(3)));hi=Vector(tuple(max(v[a] for v in points) for a in range(3)));solids.append((name,BVHTree.FromPolygons(vv,faces),lo,hi))
 result={};direction=Vector((.371,.691,.591)).normalized()
 metadata=json.loads((O.parent/'RSH12Integration20261003/Single/authoring.json').read_text());raw=json.loads((O.parent/'RSH12Integration20261003/canonical_parts.json').read_text());canonical=(rig.matrix_world@rig.pose.bones['WPN_root'].matrix@Matrix(metadata['alignment'])).inverted();root_solids=[]
 for part in raw:
  if part['name'] not in ('9_l','7_l','11_l'):continue
  points=[Vector(v) for v in part['verts']];lo=Vector(tuple(min(v[a] for v in points) for a in range(3)));hi=Vector(tuple(max(v[a] for v in points) for a in range(3)));root_solids.append((part['name'],BVHTree.FromPolygons(points,part['faces']),lo,hi))
 for i,pt in enumerate(vv):
  name=groups.get(labels.get(i),'')
  if not name.endswith('_r') or not name.startswith(('hand','thumb','index','middle','ring','pinky')):continue
  choices=[(metal,tree,lo,hi,pt) for metal,tree,lo,hi in solids if metal!='WPN_root']+[(metal,tree,lo,hi,canonical@pt) for metal,tree,lo,hi in root_solids]
  for metal,tree,lo,hi,point in choices:
   pt=point
   if any(pt[a]<lo[a] or pt[a]>hi[a] for a in range(3)):continue
   count=0;origin=pt+direction*1e-7
   for _ in range(30):
    hit,_,_,_=tree.ray_cast(origin,direction,1.)
    if hit is None:break
    count+=1;origin=hit+direction*1e-6
   if count%2:
    distance=tree.find_nearest(pt)[3]*1000;key=name+' / '+metal;item=result.setdefault(key,dict(vertices=0,max_mm=0.));item['vertices']+=1;item['max_mm']=max(item['max_mm'],distance)
 out.append(dict(time=t,skin_metal_intersections=result));print('COCK_SKIN_CONTACT',t,json.dumps(result),flush=True);ev.to_mesh_clear()
(O/'cock_surface_contacts.json').write_text(json.dumps(out,indent=2))
