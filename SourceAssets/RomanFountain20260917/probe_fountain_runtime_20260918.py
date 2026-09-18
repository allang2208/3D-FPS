"""只读取证（不写任何资产/关卡）：水面这轮到底有没有生效。

查四件事：
  1. `M_FountainWaveWater`：光照模式 / 是否世界空间法线 / WPO、法线、透明度、基础色分别接在哪个节点上 / 关键参数默认值；
  2. `SM_RomanFountain_WaterWaves`：槽位与包围盒（水面网格是否存在、材质挂上没有）；
  3. `SM_RomanFountain_20`：slot1 是否已是隐藏材质；
  4. **关卡 `RomanFountain1` 实例的组件清单**：C++ 后加的 `FountainWater` 组件在不在、它的网格是什么、可见性如何。
     （这条最关键：C++ 新增默认组件不一定自动补到已摆好的实例上。）
编辑器关闭时直接跑；开着也能跑（只读）。"""

import unreal

WAVE_MAT = "/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWater"
WAVE_INST = "/Game/Props/RomanFountain20260917/Materials/MIC_FountainWaveWater"
WAVE_MESH = "/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterWaves"
FX_MESH = "/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterFX"
MAIN_MESH = "/Game/Props/RomanFountain20260917/SM_RomanFountain_20"
LEVEL = "/Game/GameMaps/DayNight_Lighting"


def log(m):
    print("[rt] " + m)


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return "ERR:%s" % exc


def input_of(mat, mp_name):
    mp = getattr(unreal.MaterialProperty, mp_name, None)
    if mp is None:
        return "no-enum:%s" % mp_name
    try:
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(mat, mp)
        return node.get_class().get_name() if node else "None"
    except Exception as exc:  # noqa: BLE001
        return "ERR:%s" % exc


mat = unreal.EditorAssetLibrary.load_asset(WAVE_MAT) or unreal.load_asset(WAVE_MAT)
if not mat:
    log("M_FountainWaveWater MISSING")
else:
    log("M_FountainWaveWater: blend=%s shading=%s two_sided=%s tlm=%s tangent_space_normal=%s exprs=%d" % (
        prop(mat, "blend_mode"), prop(mat, "shading_model"), prop(mat, "two_sided"),
        prop(mat, "translucency_lighting_mode"), prop(mat, "tangent_space_normal"),
        len(unreal.MaterialEditingLibrary.get_material_expressions(mat) or [])))
    for name in ("MP_WORLD_POSITION_OFFSET", "MP_NORMAL", "MP_OPACITY", "MP_BASE_COLOR", "MP_EMISSIVE_COLOR"):
        log("  %-24s <- %s" % (name, input_of(mat, name)))
    for e in (unreal.MaterialEditingLibrary.get_material_expressions(mat) or []):
        cls = e.get_class().get_name()
        if "ScalarParameter" in cls:
            try:
                n = str(e.get_editor_property("parameter_name"))
                if n in ("WaveHeight", "Wave1Amp", "Wave2Amp", "NoiseStrength", "NormalSlope",
                         "OpacityBase", "FresnelOpacity", "FountainScale"):
                    log("  param %-16s = %s" % (n, e.get_editor_property("default_value")))
            except Exception:  # noqa: BLE001
                pass

inst = unreal.EditorAssetLibrary.load_asset(WAVE_INST) or unreal.load_asset(WAVE_INST)
if inst:
    par = inst.get_editor_property("parent")
    log("MIC_FountainWaveWater: parent=%s scalars=%d" % (
        par.get_name() if par else "None",
        len(inst.get_editor_property("scalar_parameter_values") or [])))

for path, label in ((WAVE_MESH, "WaterWaves"), (FX_MESH, "WaterFX"), (MAIN_MESH, "Main")):
    m = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
    if not m:
        log("%s MISSING (%s)" % (label, path))
        continue
    bb = m.get_bounds()
    slots = [m.get_material(i).get_name() if m.get_material(i) else "None"
             for i in range(len(m.get_editor_property("static_materials") or []))]
    log("%-10s tris=%d bbox=%.0fx%.0fx%.0f origin_z=%.1f slots=%s" % (
        label, m.get_num_triangles(0), bb.box_extent.x * 2, bb.box_extent.y * 2,
        bb.box_extent.z * 2, bb.origin.z, slots))

# 关卡实例的组件清单（最关键）
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les and les.load_level(LEVEL):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fountains = [a for a in actor_sub.get_all_level_actors()
                 if "ColdSteelFountain" in a.get_class().get_name()]
    log("level fountain instances: %d" % len(fountains))
    for f in fountains:
        log("  %s loc=(%.0f,%.0f,%.0f)" % (f.get_actor_label(), f.get_actor_location().x,
                                           f.get_actor_location().y, f.get_actor_location().z))
        comps = list(f.get_components_by_class(unreal.StaticMeshComponent))
        log("  StaticMeshComponents: %d" % len(comps))
        for c in comps:
            try:
                mesh = c.get_static_mesh()
                mname = mesh.get_name() if mesh else "None"
            except Exception as exc:  # noqa: BLE001
                mname = "ERR:%s" % exc
            try:
                vis = c.is_visible()
            except Exception as exc:  # noqa: BLE001
                vis = "ERR:%s" % exc
            try:
                cname = c.get_name()
            except Exception:  # noqa: BLE001
                cname = "?"
            log("    %-22s mesh=%-30s visible=%s" % (cname, mname, vis))
        nia = list(f.get_components_by_class(unreal.NiagaraComponent))
        log("  NiagaraComponents: %d %s" % (len(nia), [c.get_name() for c in nia]))
else:
    log("load_level failed")
log("done")
