import json
import unreal as u

assets = u.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game', recursive=True)
matches = []
for data in assets:
    name = str(data.asset_name).lower()
    if 'baguette' in name or 'ujqhebs' in name:
        matches.append(str(data.package_name))
u.log('BAGUETTE_IMPORTED_ASSETS ' + json.dumps({
    'assets': matches,
    'playing': u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None,
}))
