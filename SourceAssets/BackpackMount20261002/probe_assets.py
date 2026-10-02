# 校验背包资产：槽位材质、包围盒、贴图压缩设置
import unreal
U = unreal
OUT = "/Game/Characters/SovietBackpack20261002"
sm = U.load_asset("%s/SM_SovietBackpack.SM_SovietBackpack" % OUT)
for i, s in enumerate(sm.static_materials):
    print("slot", i, s.material_slot_name, s.material_interface.get_path_name() if s.material_interface else None)
b = sm.get_bounds()
print("bounds origin=%s extent=%s" % (b.origin, b.box_extent))
for n in ("T_SovietBackpack_BaseColor", "T_SovietBackpack_Normal", "T_SovietBackpack_MR"):
    t = U.load_asset("%s/%s.%s" % (OUT, n, n))
    print(n, "srgb=", t.get_editor_property("srgb"), "comp=", t.get_editor_property("compression_settings"))
