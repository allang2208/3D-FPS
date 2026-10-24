"""Read saved collision hulls for offline clearance checks without a physics scene."""
import unreal as u,json,itertools,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[];other_shapes=[]
def field(text,key):
 start=text.find(key+'=')
 if start<0:return ''
 start+=len(key)+1
 if text[start]!='(':raise RuntimeError('Unexpected serialized collision transform')
 depth=0
 for i in range(start,len(text)):
  if text[i]=='(':depth+=1
  elif text[i]==')':
   depth-=1
   if depth==0:return text[start+1:i]
 raise RuntimeError('Incomplete collision transform')
def transform_convex(hull,p):
 # Struct export preserves the private transform; no asset or property is modified.
 text=field(hull.export_text(),'Transform')
 def values(key,defaults):
  s=field(text,key);return {**defaults,**{k:float(v) for k,v in re.findall(r'([XYZW])=([-+0-9.eE]+)',s)}}
 q=values('Rotation',dict(X=0.,Y=0.,Z=0.,W=1.));t=values('Translation',dict(X=0.,Y=0.,Z=0.));s=values('Scale3D',dict(X=1.,Y=1.,Z=1.))
 x,y,z=p.x*s['X'],p.y*s['Y'],p.z*s['Z'];qx,qy,qz,qw=[q[k] for k in 'XYZW']
 tx,ty,tz=2*(qy*z-qz*y),2*(qz*x-qx*z),2*(qx*y-qy*x)
 return u.Vector(x+qw*tx+qy*tz-qz*ty+t['X'],y+qw*ty+qz*tx-qx*tz+t['Y'],z+qw*tz+qx*ty-qy*tx+t['Z'])
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 if isinstance(actor,(u.ColdSteelSlidingDoor,u.ColdSteelDoor,u.ColdSteelWindow,u.ColdSteelRevolvingDoor)):continue
 for c in actor.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh or c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION:continue
  body=c.static_mesh.get_editor_property('body_setup')
  if not body:continue
  agg=body.get_editor_property('agg_geom');ct=c.get_world_transform()
  for hull in agg.get_editor_property('convex_elems'):
   vertices=[list(ct.transform_location(transform_convex(hull,p)).to_tuple()) for p in hull.get_editor_property('vertex_data')]
   if vertices:rows.append(dict(actor=actor.get_actor_label(),component=c.get_name(),vertices=vertices))
  for box in agg.get_editor_property('box_elems'):
   centre=box.get_editor_property('center');rot=box.get_editor_property('rotation');bt=u.Transform(location=centre,rotation=rot)
   half=[box.get_editor_property(k)/2 for k in ['x','y','z']]
   vertices=[list(ct.transform_location(bt.transform_location(u.Vector(*(side[i]*half[i] for i in range(3))))).to_tuple()) for side in itertools.product([-1,1],repeat=3)]
   rows.append(dict(actor=actor.get_actor_label(),component=c.get_name(),vertices=vertices))
  for key in ['sphere_elems','sphyl_elems','tapered_capsule_elems']:
   if len(agg.get_editor_property(key)):other_shapes.append(dict(actor=actor.get_actor_label(),shape=key,count=len(agg.get_editor_property(key))))
(ROOT/'saved-collision-hulls.json').write_text(json.dumps(dict(hulls=rows,other_shapes=other_shapes),separators=(',',':')),encoding='utf8')
print('APARTMENT_COLLISION_HULLS_READ',len(rows),other_shapes)
