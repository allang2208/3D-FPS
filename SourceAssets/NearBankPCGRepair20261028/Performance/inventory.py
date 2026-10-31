from pathlib import Path
from datetime import datetime
import json,unreal as u
R=Path(__file__).resolve().parent;P=R.parent;R.mkdir(exist_ok=True)
M=json.loads((P/'publish_manifest.json').read_text());meshes={};components=[]
S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
def prop(o,n):
 try:return o.get_editor_property(n)
 except Exception:return None
for path in sorted({r['mesh'] for r in M['rows']}):
 sm=u.load_asset(path)
 if not sm:raise RuntimeError('Missing '+path)
 ns=sm.get_editor_property('nanite_settings');bb=sm.get_bounding_box();bs=sm.get_editor_property('body_setup')
 meshes[path]=dict(lod_triangles=[sm.get_num_triangles(i) for i in range(sm.get_num_lods())],nanite=prop(ns,'enabled'),fallback_percent_triangles=prop(ns,'fallback_percent_triangles'),fallback_relative_error=prop(ns,'fallback_relative_error'),min=list(bb.min.to_tuple()),max=list(bb.max.to_tuple()),materials=len(sm.static_materials),collision=str(prop(bs,'collision_trace_flag')))
assets=json.loads((P/'publish_assets.json').read_text())
for row in assets['blocks']:
 bp=u.load_asset(row['path'])
 handles={str(F.get_variable_name(F.get_data(h))):h for h in S.k2_gather_subobject_data_for_blueprint(bp)}
 for h in handles.values():
  c=F.get_object(F.get_data(h))
  if not isinstance(c,u.InstancedStaticMeshComponent) or not c.static_mesh or not c.get_instance_count():continue
  components.append(dict(bp=row['path'],name=str(F.get_variable_name(F.get_data(h))),mesh=c.static_mesh.get_path_name(),count=c.get_instance_count(),cast_shadow=prop(c,'cast_shadow'),cull_start=prop(c,'instance_start_cull_distance'),cull_end=prop(c,'instance_end_cull_distance'),profile=str(c.get_collision_profile_name()),raytracing=prop(c,'visible_in_ray_tracing'),wpo=prop(c,'evaluate_world_position_offset'),overlaps=prop(c,'generate_overlap_events'),navigation=prop(c,'can_ever_affect_navigation'),min_lod=prop(c,'min_lod'),forced_lod=prop(c,'forced_lod_model'),visible=c.is_visible(),hidden=prop(c,'hidden_in_game')))
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=u.find_object(None,'/Game/GameMaps/L_CyberpunkApartment.L_CyberpunkApartment');scene=[]
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if not a.get_actor_label().startswith('NBPCG_'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.static_mesh and c.get_instance_count():scene.append(dict(actor=a.get_actor_label(),mesh=c.static_mesh.get_path_name(),count=c.get_instance_count(),profile=str(c.get_collision_profile_name()),overlaps=prop(c,'generate_overlap_events'),navigation=prop(c,'can_ever_affect_navigation'),cast_shadow=prop(c,'cast_shadow'),cull_end=prop(c,'instance_end_cull_distance')))
(R/globals().get('OUTPUT_NAME','inventory.json')).write_text(json.dumps(dict(meshes=meshes,components=components,scene=scene,game_running=bool(ed.get_game_world()) if ed else False,dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],saved_at=datetime.now().astimezone().isoformat()),indent=2))
print('DISTRICT_COST_INVENTORY',len(meshes),len(components),sum(c['count'] for c in components))
