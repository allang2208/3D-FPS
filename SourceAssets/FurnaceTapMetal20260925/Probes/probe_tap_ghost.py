# Probe v9: ghost hunt — does the real NS path resolve to anything without a file?
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API

E = u.EditorAssetLibrary
path = '/Game/Fluids/FurnaceTapMetal20260925/NS_FurnaceTapMetal'
u.log('PROBE9 exists=%s' % E.does_asset_exist(path))
obj = u.load_asset(path)
u.log('PROBE9 load=%s' % (obj.get_path_name() if obj else None))
ar = u.AssetRegistryHelpers.get_asset_registry()
d = ar.get_asset_by_object_path(u.TopLevelAssetPath('/Game/Fluids/FurnaceTapMetal20260925', 'NS_FurnaceTapMetal'))
u.log('PROBE9 registry_valid=%s' % d.is_valid())
if d.is_valid():
    u.log('PROBE9 registry_class=%s' % d.asset_class_path.asset_name)
assets = ar.get_assets_by_path(u.TopLevelAssetPath('/Game/Fluids/FurnaceTapMetal20260925'), False)
for a in assets:
    u.log('PROBE9 registry_entry=%s.%s' % (a.package_name, a.asset_name))
u.log('PROBE9-DONE')
