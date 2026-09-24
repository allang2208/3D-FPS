import json, unreal as u
SRC_SKELETON = '/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid_Skeleton'
DST = '/Game/Props/WarehouseCrateTiers20260924/Skeletal'
open_clip = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidOpen')
close_clip = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidClose')
out = {'open_bound_skeleton': open_clip.get_editor_property('skeleton').get_path_name()==SRC_SKELETON,
       'close_bound_skeleton': close_clip.get_editor_property('skeleton').get_path_name()==SRC_SKELETON,
       'open_len': round(open_clip.get_play_length(),3), 'close_len': round(close_clip.get_play_length(),3),
       'variants': {}}
for n in ('T1_Wood','T2_StoneWood','T3_Iron','T4_IronGold','T5_SilverGem'):
    m = u.load_asset('%s/SK_WarehouseCrate_%s' % (DST, n))
    skel_ok = m.get_editor_property('skeleton').get_path_name()==SRC_SKELETON
    slots = m.get_editor_property('materials')
    mats = sorted({(str(s.get_editor_property('material_slot_name')),
                    s.get_editor_property('material_interface').get_name() if s.get_editor_property('material_interface') else 'NONE')
                   for s in slots})
    out['variants']['SK_WarehouseCrate_'+n] = {'shared_skeleton': skel_ok, 'slot_count': len(slots),
        'n_none': sum(1 for _,mm in mats if mm=='NONE'),
        'distinct_mats': sorted({mm for _,mm in mats})}
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/sk_readback.json','w').write(json.dumps(out, indent=1))
