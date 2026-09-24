import unreal as u
reg = u.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_all_assets():
    pp = str(a.package_path)
    if 'RitualV8' in pp and 'Material' in str(a.asset_class_path.asset_name):
        m = u.EditorAssetLibrary.load_asset(pp + '/' + str(a.asset_name))
        if m is not None:
            print('TS', str(a.asset_name), m.get_editor_property('two_sided'), flush=True)
