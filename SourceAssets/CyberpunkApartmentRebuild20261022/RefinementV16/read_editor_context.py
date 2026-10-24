"""Read only the active world and target dependencies needed for authoring."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=s.get_editor_world()
report=dict(current_map=world.get_path_name() if world else None,play_world=bool(s.get_game_world()),dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],actors=[])
if world and world.get_path_name().startswith('/Game/GameMaps/L_CyberpunkApartment.'):
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=a.get_actor_label()
  if not (label.startswith(('AP8_','AP9_','CITY_','BAY_')) or isinstance(a,u.PlayerStart)):continue
  row=dict(label=label,location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),components=[])
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   b=c.static_mesh.get_bounding_box()
   row['components'].append(dict(mesh=c.static_mesh.get_path_name(),bounds=[list(b.min.to_tuple()),list(b.max.to_tuple())],materials=[m.get_path_name() if m else None for m in c.get_materials()]))
  report['actors'].append(row)
(R/'editor-context.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('AP16_AUTHORING_CONTEXT',report['current_map'],report['play_world'],len(report['actors']))
