import json, unreal as u
skel = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid_Skeleton')
out = {}
out['methods'] = [x for x in dir(skel) if 'bone' in x.lower() or 'skeleton' in x.lower()]
names = []
try:
    n = skel.get_bone_count()
    for i in range(n):
        try: names.append(skel.get_bone_name(i))
        except Exception as e: names.append('ERR' + str(e))
except Exception as e:
    out['count_err'] = str(e)
out['bone_names'] = names
out['tree_props'] = []
for b in skel.get_editor_property('bone_tree')[:1]:
    out['tree_props'] = [x for x in dir(b) if not x.startswith('_')]
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/bone_names.json','w').write(json.dumps(out, indent=1))
