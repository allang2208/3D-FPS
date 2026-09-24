import json, unreal as u
t1 = u.load_asset('/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood')
mat = u.load_asset('/Game/Props/WarehouseCrateTiers20260924/Materials/M_Crate_Wood')
slots = t1.get_editor_property('materials')
r0 = {'before': str(slots[0].get_editor_property('material_interface').get_path_name())}
slot0 = slots[0]
slot0.set_editor_property('material_interface', mat)
slots[0] = slot0
t1.set_editor_property('materials', slots)
after = t1.get_editor_property('materials')[0].get_editor_property('material_interface')
r0['after_set'] = str(after.get_path_name()) if after else None
# struct direct-mutation attempt too
try:
    s2 = t1.get_editor_property('materials')
    s2[1].set_editor_property('material_interface', mat)
    r0['direct_index_set'] = str(s2[1].get_editor_property('material_interface').get_path_name())
except Exception as e:
    r0['direct_err'] = str(e)
u.EditorLoadingAndSavingUtils.save_packages([u.load_package('/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood')], False)
r0['saved'] = True
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/sk_settest.json','w').write(json.dumps(r0, indent=1))
