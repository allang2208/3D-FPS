"""Resolve remaining bedroom furniture identities from the current formal world."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=s.get_editor_world()
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_CyberpunkApartment':
    if s.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve active play or unsaved maps')
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        path=c.static_mesh.get_path_name()
        if 'bed' not in path.lower() and 'master' not in label.lower():continue
        rows.append(dict(actor=label,actor_class=a.get_class().get_name(),component=c.get_name(),mesh=path,
          position=list(c.get_world_location().to_tuple()),scale=list(c.get_world_scale().to_tuple())))
(R/'remaining-source.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('BEDROOM_SOURCE_COMPONENTS',len(rows))
