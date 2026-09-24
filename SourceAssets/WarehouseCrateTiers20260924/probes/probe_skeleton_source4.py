import unreal as u
reg = u.AssetRegistryHelpers.get_asset_registry()
want = []
for a in reg.get_all_assets():
    pp = str(a.package_path); cls = str(a.asset_class_path.asset_name); nm = str(a.asset_name)
    if 'Warehouse20260909' in pp and 'warehouse_chest_rigid' in pp and cls in ('SkeletalMesh','Skeleton','AnimSequence'):
        path = pp if nm == pp.split('/')[-1] else pp + '/' + nm
        want.append((cls, path))
r8 = [w for w in want if 'RitualV8' in w[1]]
skel = u.load_asset(next(p for c,p in r8 if c=='Skeleton'))
tree = skel.get_editor_property('bone_tree')
b0 = tree[0]
probe = [x for x in dir(b0) if 'name' in x.lower() or 'bone' in x.lower()]
print('BONE_ATTRS', probe, flush=True)
def bname(n):
    for att in ('bone_name','get_bone_name','name'):
        try:
            v = getattr(n, att)
            return str(v() if callable(v) else n.get_editor_property(att))
        except Exception: continue
    return '?'
print('BONES', [bname(n) for n in tree], flush=True)
sm = u.load_asset(next(p for c,p in r8 if c=='SkeletalMesh'))
print('MESH', sm.get_path_name(), 'SKEL_OK', sm.get_editor_property('skeleton').get_path_name()==skel.get_path_name(), flush=True)
print('MESH_MATS', [(str(m.get_editor_property('material_set_name')), m.get_editor_property('material_index'), (m.get_editor_property('material') or None) and m.get_editor_property('material').get_path_name()) for m in sm.get_editor_property('materials')], flush=True)
for c,p in r8:
    if c=='AnimSequence':
        an=u.load_asset(p); print('ANIM', an.get_name(), 'len', round(an.get_play_length(),3), 'skel_match', an.get_editor_property('skeleton').get_path_name()==skel.get_path_name(), flush=True)
