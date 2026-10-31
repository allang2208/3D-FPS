from pathlib import Path
import json, unreal as u
R=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    p=a.get_actor_location();label=a.get_actor_label()
    if not ('Kitchen' in label or label.startswith('KP_') or (1000<p.x<1650 and -2200<p.y<-1850 and p.z<290)):continue
    row=dict(label=label,cls=a.get_class().get_name(),pos=list(p.to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),components=[])
    if isinstance(a,u.ColdSteelSceneContainer):
        row['id']=str(a.get_editor_property('container_id'))
        row['hinge']=str(a.door_hinge.get_relative_transform())
        row['opening']={k:str(a.get_editor_property(k)) for k in ['opening_motion','opened_yaw','initial_open_fraction','drawer_travel']}
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        row['components'].append(dict(name=c.get_name(),mesh=m.get_path_name() if m else None,relative=str(c.get_relative_transform()),world=str(c.get_world_transform()),bounds=str(m.get_bounding_box()) if m else None,materials=[str(x.get_path_name()) if x else None for x in c.get_materials()],collision=str(c.get_collision_enabled())))
    rows.append(row)
(R/'scene_before.json').write_text(json.dumps(dict(cable_component=hasattr(u,'CableComponent'),cable_actor=hasattr(u,'CableActor'),actors=rows),indent=2),encoding='utf8')
print('KITCHEN_SCOPE_READ',len(rows))
