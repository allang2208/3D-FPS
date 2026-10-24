"""Check the native door's final slide volumes against saved collision; no PIE."""
from pathlib import Path
import unreal as u,json
ROOT=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
control=u.SystemLibrary.box_trace_multi_for_objects(world,u.Vector(540,-360,144),u.Vector(630,-360,144),u.Vector(2,2,2),u.Rotator(),
 [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],False,[],u.DrawDebugTrace.NONE,True)
control_actors=[]
for hit in control or []:
 control_actors.extend(v.get_actor_label() for v in u.GameplayStatics.break_hit_result(hit) if isinstance(v,u.Actor))
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.ColdSteelSlidingDoor):
 label=a.get_actor_label()
 if not label.startswith('Door_'):continue
 components={c.get_name():c for c in a.get_components_by_class(u.StaticMeshComponent)}
 c=components['LeafLeft'];bounds=c.static_mesh.get_bounding_box();half=(bounds.max-bounds.min)*.5
 scale=a.get_actor_scale3d();half=u.Vector(half.x,half.y*.5,half.z)
 ext=u.Vector(max(1,half.x*abs(scale.x)-2),max(1,half.y*abs(scale.y)-2),max(1,half.z*abs(scale.z)-4))
 travel=a.get_editor_property('slide_distance_cm');transform=a.get_actor_transform();ends=[]
 for side in [-1,1]:
  centre=transform.transform_location(u.Vector(0,side*(half.y+travel),half.z))
  result=u.SystemLibrary.box_trace_multi_for_objects(world,centre,centre+u.Vector(0,0,.01),ext,a.get_actor_rotation(),
    [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],False,[a],u.DrawDebugTrace.NONE,True)
  # Python returns the out-hit array plus the blocking flag.
  def collect(value):
   if isinstance(value,u.HitResult):return [value]
   if isinstance(value,(tuple,list,u.Array)):
    return [hit for item in value for hit in collect(item)]
   return []
  blockers=[]
  for hit in collect(result):
   actor=next((v for v in u.GameplayStatics.break_hit_result(hit) if isinstance(v,u.Actor)),None)
   if actor and actor!=a and not isinstance(actor,(u.ColdSteelSlidingDoor,u.ColdSteelDoor,u.ColdSteelWindow,u.ColdSteelRevolvingDoor)):
    blockers.append(actor.get_actor_label())
  ends.append(dict(side=side,centre=list(centre.to_tuple()),blocking_actors=sorted(set(blockers))))
 rows.append(dict(door=label,ends=ends,leaf_thickness_cm=half.x*2*abs(scale.x),travel_cm=travel))
report=dict(doors=rows,door_count=len(rows),blocked=[r['door'] for r in rows if any(e['blocking_actors'] for e in r['ends'])],
 positive_control_actors=control_actors,query_scene_valid='AP_Wall_Master' in control_actors,
 method='Saved-world static collision queries using the same final bounds as ColdSteelSlidingDoor::IsSlideBlocked; no door tick or play simulation',game_run=False,rendered=False)
(ROOT/'door-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('APARTMENT_V5_POCKET_CLEARANCE',report['door_count'],report['blocked'])
