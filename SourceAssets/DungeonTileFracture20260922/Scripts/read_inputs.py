"""Read the eight installed wall references needed for the ceramic revision."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
previous=json.loads((ROOT.parent/'DungeonWallRelief20260922/Authored/geometry-manifest.json').read_text())
labels={row['actor'] for row in previous['objects']}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not editor or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():
    raise RuntimeError('Requires FPSGAME editor host')
data=dict(world=editor.get_editor_world().get_path_name(),gameplay=bool(editor.get_game_world()),actors=[])
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label() not in labels:continue
    comp=actor.get_component_by_class(u.StaticMeshComponent)
    if not comp or not comp.static_mesh:raise RuntimeError('Missing wall mesh '+actor.get_actor_label())
    data['actors'].append(dict(label=actor.get_actor_label(),mesh=comp.static_mesh.get_path_name(),
        slots=[dict(name=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None)
               for s in comp.static_mesh.get_editor_property('static_materials')],
        overrides=[m.get_path_name() if m else None for m in comp.get_editor_property('override_materials')]))
if len(data['actors'])!=len(labels):raise RuntimeError('Required wall actors are not in the loaded editor map')
(ROOT/'Sources').mkdir(parents=True,exist_ok=True)
(ROOT/'Sources/scene-inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
