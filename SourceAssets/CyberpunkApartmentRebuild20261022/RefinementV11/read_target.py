"""Read the saved host tower and apartment interface dimensions for replacement authoring."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent;MAP='/Game/GameMaps/L_CyberpunkApartment'
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if s and s.get_game_world():raise RuntimeError('Preserve active play world')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
world=s.get_editor_world() if s else None
if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
report=dict(map=MAP,actors=[])
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 label=a.get_actor_label()
 if not (label=='CITY_our_tower' or label.startswith(('AP_Floor','AP_Ceiling','AP_Wall','AP_Facade','AP_Window','AP_Balcony','AP_Entry','AP_Gym','AP_Bath','AP_Rail'))):continue
 row=dict(label=label,location=list(a.get_actor_location().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),meshes=[])
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh:continue
  box=c.static_mesh.get_bounding_box();xf=c.get_world_transform()
  vs=[u.MathLibrary.transform_location(xf,u.Vector(x,y,z)) for x in (box.min.x,box.max.x) for y in (box.min.y,box.max.y) for z in (box.min.z,box.max.z)]
  bounds=[[min(getattr(v,axis) for v in vs) for axis in ('x','y','z')],[max(getattr(v,axis) for v in vs) for axis in ('x','y','z')]]
  row['meshes'].append(dict(mesh=c.static_mesh.get_path_name(),world_bounds_cm=bounds,local_bounds_cm=[list(box.min.to_tuple()),list(box.max.to_tuple())],materials=[m.get_path_name() if m else None for m in c.get_materials()],collision_profile=str(c.get_collision_profile_name())))
 report['actors'].append(row)
(R/'source-bindings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('AP11_HOST_SOURCE_READ',len(report['actors']))
