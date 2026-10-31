"""Read-only editor/PIE context; never stops play or writes project assets."""
from pathlib import Path
import json
import unreal as u
root = Path(__file__).resolve().parent
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
rows = []
for world in u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    rows.append(dict(package=world.get_path_name(), outer=world.get_outer().get_path_name() if world.get_outer() else None))
result = dict(
    read_only=True,
    editor_world=editor.get_editor_world().get_path_name() if editor and editor.get_editor_world() else None,
    game_world=editor.get_game_world().get_path_name() if editor and editor.get_game_world() else None,
    dirty_maps=rows,
    package_on_disk=u.EditorAssetLibrary.does_asset_exist('/Game/Props/CyberpunkApartmentKitchen20261024/Meshes/SM_KP_BaseBody'),
    loaded_asset=bool(u.find_object(None, '/Game/Props/CyberpunkApartmentKitchen20261024/Meshes/SM_KP_BaseBody')),
    loaded_project=u.Paths.project_dir(),
)
(root / 'bridge-context.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print('KITCHEN_EDITOR_CONTEXT ' + json.dumps(result), flush=True)
