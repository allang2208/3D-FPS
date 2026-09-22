"""Restore only the five retired banks whose state was not saved in their actor packages."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
TARGET = '/Game/GameMaps/L_Dungeon_Prototype'
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = editor.get_editor_world()
if editor.get_game_world() or not world or world.get_path_name().split('.')[0] != TARGET:
    raise RuntimeError('Saved dungeon must be open in edit mode')
dirty = u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:
    raise RuntimeError('Preserve existing unsaved map edits: ' + ', '.join(p.get_name() for p in dirty))
labels = json.loads((ROOT / 'Authored/manifest.json').read_text())['hidden_previous']
actors = {a.get_actor_label(): a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()}
targets = [(actors[label], actors[label].get_component_by_class(u.StaticMeshComponent)) for label in labels]
for actor, component in targets:
    actor.modify()
    component.modify()
    actor.set_actor_hidden_in_game(True)
    actor.set_is_temporarily_hidden_in_editor(True)
    actor.set_actor_enable_collision(False)
    component.set_visibility(False)
editor.set_level_viewport_camera_info(
    u.Vector(1810, -320, 165),
    u.MathLibrary.find_look_at_rotation(u.Vector(1810, -320, 165), u.Vector(1900, -950, 145)))
if not level_editor.save_current_level():
    raise RuntimeError('Dungeon save failed; live edits retained')
receipt = {
    'stage': 'map_saved', 'map': TARGET, 'saved_at': datetime.now().isoformat(),
    'restored_hidden_actors': labels, 'unchanged_new_actors': 40,
    'fix': 'Mark actors and components modified before saving persistent visibility and collision',
    'viewport': 'ruin entrance', 'tests_run': False, 'screenshots_taken': False,
}
path = ROOT / 'Receipts/recovery-restored.json'
path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('DUNGEON_RECOVERY_SAVED ' + json.dumps(receipt))
