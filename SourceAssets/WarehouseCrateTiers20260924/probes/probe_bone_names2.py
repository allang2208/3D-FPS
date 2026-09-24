import json, unreal as u
sm = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid')
skel = sm.get_editor_property('skeleton')
out = {}
try:
    out['mesh_methods'] = [x for x in dir(sm) if 'bone' in x.lower()][:20]
    n = sm.get_bone_count()
    out['mesh_bones'] = [str(sm.get_bone_name(i)) for i in range(n)]
except Exception as e:
    out['mesh_err'] = str(e)
try:
    tree = skel.get_editor_property('bone_tree')
    out['tree_dicts'] = [b.to_dict() for b in tree]
except Exception as e:
    out['tree_err'] = str(e)
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/bone_names.json','w').write(json.dumps(out, indent=1))
