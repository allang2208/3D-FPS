import unreal as u
reg = u.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_all_assets():
    pp = str(a.package_path)
    cls = str(a.asset_class_path.asset_name)
    if 'warehouse_chest' in pp.lower() or ('RitualV8' in pp and cls in ('SkeletalMesh','Skeleton','AnimSequence','PhysicsAsset')):
        print('ASSET', cls, pp, flush=True)
skel = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/warehouse_chest_rigid/warehouse_chest_rigid_Skeleton')
if skel is None:
    skel = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid_Skeleton')
if skel:
    print('SKELETON_OK', skel.get_path_name(), flush=True)
    print('BONES', [b.get_editor_property('name') for b in skel.get_editor_property('bone_tree')], flush=True)
sm = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/warehouse_chest_rigid/warehouse_chest_rigid')
if sm is None:
    sm = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid')
if sm:
    s2 = sm.get_editor_property('skeleton')
    print('CHEST_MESH', sm.get_path_name(), 'skeleton', s2.get_path_name() if s2 else None, flush=True)
    for c in sm.get_editor_property('skeletal_mesh_anims_to_export') or []:
        pass
    an = unreal_skel = None
    print('MATS', [str(m.get_path_name()) if m else None for m in sm.get_editor_property('materials')], flush=True)
