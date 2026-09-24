import unreal as u
reg = u.AssetRegistryHelpers.get_asset_registry()
want = []
for a in reg.get_all_assets():
    pp = str(a.package_path)
    cls = str(a.asset_class_path.asset_name)
    if 'Warehouse20260909' in pp and 'warehouse_chest_rigid' in pp and cls in ('SkeletalMesh','Skeleton','AnimSequence') and 'RitualV8' in pp:
        want.append((cls, pp + '.' + str(a.asset_name)))
for cls, path in sorted(want): print(cls, path, flush=True)
skelpath = next(p for c,p in want if c=='Skeleton')
skel = u.load_asset(skelpath.split('.')[0])
print('BONES', [b.get_editor_property('name') for b in skel.get_editor_property('bone_tree')], flush=True)
sm = u.load_asset(next(p for c,p in want if c=='SkeletalMesh').split('.')[0])
print('MESH', sm.get_name(), 'skel_match', sm.get_editor_property('skeleton').get_path_name()==skel.get_path_name(), flush=True)
print('MESH_MATS', [str(m.get_path_name()) if m else None for m in sm.get_editor_property('materials')], flush=True)
for c,p in want:
    if c=='AnimSequence':
        an=u.load_asset(p.split('.')[0]); print('ANIM', an.get_name(), 'len', an.get_play_length(), flush=True)
