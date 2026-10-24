"""Read saved simple collisions through GeometryScript; no physics scene required."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[];other_shapes=[];cache={}
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 if isinstance(actor,(u.ColdSteelSlidingDoor,u.ColdSteelDoor,u.ColdSteelWindow,u.ColdSteelRevolvingDoor)):continue
 for c in actor.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh or c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION:continue
  mesh=c.static_mesh;path=mesh.get_path_name()
  if path not in cache:
   collision=u.GeometryScript_Collision.get_simple_collision_from_static_mesh(mesh)
   count=u.GeometryScript_Collision.get_simple_collision_shape_count(collision)
   parts=[]
   if count:
    dm=u.GeometryScript_Primitives.append_simple_collision_shapes(u.DynamicMesh(),u.GeometryScriptPrimitiveOptions(),u.Transform(),collision,u.GeometryScriptSimpleCollisionTriangulationOptions())
    _, islands=u.GeometryScript_MeshDecomposition.split_mesh_by_components(dm,None)
    for island in islands:
     _,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(island,True)
     parts.append(list(u.GeometryScript_List.convert_vector_list_to_array(positions)))
   cache[path]=parts
  transform=c.get_world_transform()
  for points in cache[path]:
   rows.append(dict(actor=actor.get_actor_label(),component=c.get_name(),vertices=[list(transform.transform_location(p).to_tuple()) for p in points]))
  if not cache[path]:other_shapes.append(dict(actor=actor.get_actor_label(),component=c.get_name(),reason='no simple collision in saved asset'))
(ROOT/'saved-collision-hulls.json').write_text(json.dumps(dict(hulls=rows,other_shapes=other_shapes),separators=(',',':')),encoding='utf8')
print('APARTMENT_COLLISION_HULLS_READ',len(rows),other_shapes)
