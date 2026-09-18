"""只读探测（不写任何资产）：水面材质当前的光照模式/混合模式/表达式数与关键参数默认值，
以及 `SceneTextureId` 枚举的真实成员名。用来确认"水读成固体"的根因假设。

编辑器开着也能跑（只读，不触发保存）。"""

import unreal

MAT = "/Game/Props/RomanFountain20260917/Materials/M_FountainWater"
INST = "/Game/Props/RomanFountain20260917/Materials/MIC_FountainWater"
MESH = "/Game/Props/RomanFountain20260917/SM_RomanFountain_20"


def log(m):
    print("[probe] " + m)


log("SceneTextureId members: %s" % [n for n in dir(unreal.SceneTextureId) if n.startswith("PPI")])
log("TranslucencyLightingMode members: %s"
    % [n for n in dir(unreal.TranslucencyLightingMode) if n.startswith("TLM")])

mat = unreal.EditorAssetLibrary.load_asset(MAT) or unreal.load_asset(MAT)
if not mat:
    log("M_FountainWater 不在资产里（还没烘）")
else:
    def prop(name):
        try:
            return mat.get_editor_property(name)
        except Exception as exc:  # noqa: BLE001
            return "ERR:%s" % exc

    log("M_FountainWater: blend=%s shading=%s two_sided=%s tlm=%s" % (
        prop("blend_mode"), prop("shading_model"), prop("two_sided"),
        prop("translucency_lighting_mode")))
    exprs = unreal.MaterialEditingLibrary.get_material_expressions(mat) or []
    log("expressions=%d" % len(exprs))
    for e in exprs:
        cls = e.get_class().get_name()
        if "ScalarParameter" in cls or "VectorParameter" in cls:
            try:
                log("  %s = %s" % (e.get_editor_property("parameter_name"),
                                   e.get_editor_property("default_value")))
            except Exception:  # noqa: BLE001
                pass
        if "SceneTexture" in cls:
            try:
                log("  SceneTexture id = %s" % e.get_editor_property("scene_texture_id"))
            except Exception as exc:  # noqa: BLE001
                log("  SceneTexture id readback failed: %s" % exc)

inst = unreal.EditorAssetLibrary.load_asset(INST) or unreal.load_asset(INST)
if inst:
    parent = inst.get_editor_property("parent")
    log("MIC_FountainWater parent=%s scalar_overrides=%d" % (
        parent.get_name() if parent else "None",
        len(inst.get_editor_property("scalar_parameter_values") or [])))

mesh = unreal.EditorAssetLibrary.load_asset(MESH) or unreal.load_asset(MESH)
if mesh:
    slots = [mesh.get_material(i).get_name() if mesh.get_material(i) else "None"
             for i in range(len(mesh.get_editor_property("static_materials") or []))]
    bb = mesh.get_bounds()
    log("fountain mesh slots=%s bbox=%.0fx%.0fx%.0f origin_z=%.1f" % (
        slots, bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2, bb.origin.z))
log("done")
