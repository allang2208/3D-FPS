"""Read-only editor state probe; no map, asset or gameplay changes."""
from pathlib import Path
import json
import unreal as u
root = Path(__file__).resolve().parent
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_editor_world() if editor else None
result = dict(
    read_only=True,
    project=u.Paths.project_dir(),
    map=world.get_path_name() if world else None,
    pie=bool(editor and editor.get_game_world()),
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    base_asset=u.EditorAssetLibrary.does_asset_exist('/Game/Props/CyberpunkApartmentKitchen20261024/Meshes/SM_KP_BaseBody'),
    door_asset=u.EditorAssetLibrary.does_asset_exist('/Game/Props/CyberpunkApartmentKitchen20261024/Meshes/SM_KP_FridgeUpperDoor'),
)
(root / 'bridge-probe.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print('KITCHEN_EDITOR_PROBE ' + json.dumps(result), flush=True)
