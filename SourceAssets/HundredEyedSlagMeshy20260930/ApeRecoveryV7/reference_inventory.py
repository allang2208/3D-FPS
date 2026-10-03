"""Read the current map's monster references; never modify actors or assets."""
import json
from pathlib import Path
import unreal as u

out = Path(__file__).resolve().parent
rows = []
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    kind = actor.get_class().get_name()
    tags = [str(t) for t in actor.tags]
    if not any(token in (kind+' '+' '.join(tags)).lower() for token in ('monster','mutant','zombie','hundredeyed','rampage','gorilla','wolf')):
        continue
    meshes = []
    for component in actor.get_components_by_class(u.SkeletalMeshComponent):
        mesh = component.get_editor_property('skeletal_mesh_asset')
        if mesh:
            meshes.append(mesh.get_path_name())
    rows.append({'label':actor.get_actor_label(), 'class':kind, 'meshes':meshes})
report = {'current_map_monsters':rows, 'asset_or_actor_changes':False}
(out/'map_monster_references.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('CURRENT_MAP_MONSTER_REFERENCES '+json.dumps(rows[:12], ensure_ascii=False))
