import unreal as u
base='/Game/ColdSteelUI/Warehouse20260909/RitualV8/'
reg = u.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_all_assets():
    pp = str(a.package_path)
    if 'RitualV8' in pp and a.asset_class and 'Material' in str(a.asset_class.get_name()):
        m = u.EditorAssetLibrary.load_asset(pp + '/' + str(a.asset_name))
        if m is not None:
            try: print('TS', str(a.asset_name), m.get_editor_property('two_sided'), flush=True)
            except Exception as e: print('TSERR', str(a.asset_name), e, flush=True)
