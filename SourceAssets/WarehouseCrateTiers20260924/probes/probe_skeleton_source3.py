import unreal as u
reg = u.AssetRegistryHelpers.get_asset_registry()
want = []
for a in reg.get_all_assets():
    pp = str(a.package_path); cls = str(a.asset_class_path.asset_name); nm = str(a.asset_name)
    if 'Warehouse20260909' in pp and 'warehouse_chest_rigid' in pp and cls in ('SkeletalMesh','Skeleton','AnimSequence'):
        path = pp if nm == pp.split('/')[-1] else pp + '/' + nm
        want.append((cls, path))
for cls, path in sorted(want): print('A', cls, path, flush=True)
r8 = [w for w in want if 'RitualV8' in w[1]]
skel = u.load_asset(next(p for c,p in r8 if c=='Skeleton'))
print('BONES', [str(b.get_editor_property('name')) for b in skel.get_editor_property('bone_tree')], flush=True)
sm = u.load_asset(next(p for c,p in r8 if c=='SkeletalMesh'))
print('MESH', sm.get_path_name(), 'SKEL_OK', sm.get_editor_property('skeleton').get_path_name()==skel.get_path_name(), flush=True)
print('MESH_MATS', [str(m.get_path_name()) if m else None for m in sm.get_editor_property('materials')], flush=True)
for c,p in r8:
    if c=='AnimSequence':
        an=u.load_asset(p); print('ANIM', an.get_name(), 'len', an.get_play_length(), 'skel', an.get_editor_property('skeleton').get_path_name()==skel.get_path_name(), flush=True)
