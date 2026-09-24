import unreal as u
ROOT='/Game/Props/WarehouseCrateTiers20260924'
names=['SM_WarehouseCrate_T1_Wood','SM_WarehouseCrate_T2_StoneWood','SM_WarehouseCrate_T3_Iron','SM_WarehouseCrate_T4_IronGold','SM_WarehouseCrate_T5_SilverGem']
for n in names:
    path=ROOT+'/'+n
    obj=u.load_asset(path)  # ghost is still in memory: this returns it
    print('GHOST', n, obj, obj.get_class().get_name() if obj else None, flush=True)
    if obj:
        ok=u.EditorAssetLibrary.delete_loaded_asset(obj)
        print('DELETE_LOADED', n, ok, flush=True)
u.EditorAssetLibrary.scan_paths_direct(['Game/Props/WarehouseCrateTiers20260924'], False)
for n in names:
    print('EXISTS_AFTER', n, u.EditorAssetLibrary.does_asset_exist(ROOT+'/'+n), flush=True)
