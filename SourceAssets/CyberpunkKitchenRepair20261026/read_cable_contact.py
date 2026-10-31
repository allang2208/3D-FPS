from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
w=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
r={}
for label in ['KP_Counter','AP_Kitchen_Coffee','AP_Kitchen_Kettle','KR_Cable_Coffee','KR_Cable_Kettle']:
    a=actors[label];c=a.cable_component if isinstance(a,u.CableActor) else a.static_mesh_component
    row=dict(position=list(a.get_actor_location().to_tuple()),profile=str(c.get_collision_profile_name()),enabled=str(c.get_collision_enabled()),object_type=str(c.get_collision_object_type()),world_static=str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_WORLD_STATIC)),world_dynamic=str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_WORLD_DYNAMIC)))
    if isinstance(c,u.StaticMeshComponent):
        m=c.static_mesh;b=m.get_editor_property('body_setup');geom=b.get_editor_property('agg_geom')
        row.update(mesh=m.get_path_name(),bounds=str(m.get_bounding_box()),collision_trace=str(b.get_editor_property('collision_trace_flag')),boxes=[dict(center=list(q.get_editor_property('center').to_tuple()),size=[q.get_editor_property(k) for k in ['x','y','z']]) for q in geom.get_editor_property('box_elems')])
    else:row['parameters']={k:str(c.get_editor_property(k)) for k in ['cable_length','num_segments','cable_width','enable_collision','solver_iterations','substep_time','enable_stiffness','collision_friction','skip_cable_update_when_not_visible','end_location']}
    r[label]=row
(R/'cable_contact_before.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print('KITCHEN_CABLE_CONTACT_READ')
