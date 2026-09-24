import json, unreal as u
src = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid')
t1 = u.load_asset('/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood')
rows = []
for s_src, s_t1 in zip(src.get_editor_property('materials'), t1.get_editor_property('materials')):
    mi_s = s_src.get_editor_property('material_interface'); mi_t = s_t1.get_editor_property('material_interface')
    rows.append((str(s_src.get_editor_property('material_slot_name')),
                 mi_s.get_path_name() if mi_s else None,
                 mi_t.get_path_name() if mi_t else None))
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/sk_mats_compare.json','w').write(json.dumps(rows, indent=1))
