"""Read the wall inputs needed for this authoring pass; no scene changes."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'Sources').mkdir(parents=True, exist_ok=True)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not editor:
    raise RuntimeError('This operation requires the editor, not a game Python host')
data = dict(project=u.Paths.project_dir(), world=editor.get_editor_world().get_path_name(),
            gameplay=bool(editor.get_game_world()), actors=[], materials={})
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if not actor.get_actor_label().startswith('DGN_AV2_'):
        continue
    comp = actor.get_component_by_class(u.StaticMeshComponent)
    if not comp or not comp.static_mesh or not comp.static_mesh.get_name().endswith('_Tiles'):
        continue
    mesh = comp.static_mesh
    slots = [dict(name=str(s.material_slot_name), material=s.material_interface.get_path_name() if s.material_interface else None)
             for s in mesh.get_editor_property('static_materials')]
    data['actors'].append(dict(label=actor.get_actor_label(), mesh=mesh.get_path_name(), slots=slots,
                              overrides=[m.get_path_name() if m else None for m in comp.get_editor_property('override_materials')]))
data['dirty'] = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(ROOT/'Sources/scene-inputs.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data))
