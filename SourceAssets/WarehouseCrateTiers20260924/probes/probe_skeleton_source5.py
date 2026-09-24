import json, unreal as u
out = {}
reg = u.AssetRegistryHelpers.get_asset_registry()
want = []
for a in reg.get_all_assets():
    pp = str(a.package_path); cls = str(a.asset_class_path.asset_name); nm = str(a.asset_name)
    if 'Warehouse20260909' in pp and 'warehouse_chest_rigid' in pp and cls in ('SkeletalMesh','Skeleton','AnimSequence'):
        out_path = pp if nm == pp.split('/')[-1] else pp + '/' + nm
        want.append([cls, out_path])
out['assets'] = want
r8 = [w for w in want if 'RitualV8' in w[1]]
skel = u.load_asset(next(p for c,p in r8 if c=='Skeleton'))
out['skeleton'] = skel.get_path_name()
out['bone_attrs'] = [x for x in dir(list(skel.get_editor_property('bone_tree'))[0]) if 'name' in x.lower() or 'bone' in x.lower()]
def bname(n):
    try: return str(n.get_editor_property('bone_name'))
    except Exception:
        try: return str(n.get_bone_name())
        except Exception: return None
out['bones'] = [bname(x) for x in skel.get_editor_property('bone_tree')]
sm = u.load_asset(next(p for c,p in r8 if c=='SkeletalMesh'))
out['mesh'] = sm.get_path_name()
out['mesh_skel_match'] = sm.get_editor_property('skeleton').get_path_name() == skel.get_path_name()
anims = []
for c,p in r8:
    if c=='AnimSequence':
        an = u.load_asset(p)
        anims.append({'name': an.get_name(), 'len': an.get_play_length(),
                      'skel_match': an.get_editor_property('skeleton').get_path_name() == skel.get_path_name()})
out['anims'] = anims
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/skeleton_probe.json','w',encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
