"""只读探测：为什么水面仍读成固体。

1. `M_Caustics` / `MIC_FountainCaustics`（盆底衬底）：混合模式、光照模型、是否不透明 —— 若它是不透明暗板，
   透过半透明水面看到的就是"一块实心地板"，再大的波浪也改不了观感。
2. 关卡实例的 `FountainWater` 组件：网格 / 槽 0 材质 / 可见性（用属性名 `static_mesh`，上一版探针的 API 名写错了）。
3. 存档里的**构件**清单：今天改逻辑构件之前从面板摆下的喷泉是普通静态构件（现在水槽=隐藏材质 → 干盆）。
"""

import glob
import os
import re

import unreal

CAUSTICS_MAT = "/Game/WaterMaterials/Materials/M_Caustics"
CAUSTICS_INST = "/Game/Props/RomanFountain20260917/Materials/MIC_FountainCaustics"
LEVEL = "/Game/GameMaps/DayNight_Lighting"


def log(m):
    print("[flat] " + m)


def show(path, label):
    a = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
    if not a:
        log("%s MISSING %s" % (label, path))
        return None
    def p(n):
        try:
            return a.get_editor_property(n)
        except Exception as exc:  # noqa: BLE001
            return "ERR:%s" % exc
    log("%s: class=%s blend=%s shading=%s two_sided=%s opacity_mask_clip=%s" % (
        label, a.get_class().get_name(), p("blend_mode"), p("shading_model"),
        p("two_sided"), p("opacity_mask_clip_value")))
    try:
        par = p("parent")
        if par:
            log("   parent=%s" % par.get_name())
    except Exception:  # noqa: BLE001
        pass
    try:
        exprs = unreal.MaterialEditingLibrary.get_material_expressions(a) or []
        for e in exprs:
            cls = e.get_class().get_name()
            if "VectorParameter" in cls or "ScalarParameter" in cls:
                try:
                    log("   param %-18s = %s" % (e.get_editor_property("parameter_name"),
                                                 e.get_editor_property("default_value")))
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        log("   expr scan failed: %s" % exc)
    return a


show(CAUSTICS_MAT, "M_Caustics")
show(CAUSTICS_INST, "MIC_FountainCaustics")

# 关卡实例的水面组件（正确的属性名）
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les and les.load_level(LEVEL):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actor_sub.get_all_level_actors():
        if "ColdSteelFountain" not in a.get_class().get_name():
            continue
        log("fountain %s loc=(%.0f,%.0f,%.0f)" % (a.get_actor_label(), a.get_actor_location().x,
                                                 a.get_actor_location().y, a.get_actor_location().z))
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            try:
                mesh = c.get_editor_property("static_mesh")
            except Exception as exc:  # noqa: BLE001
                mesh = None
                log("   %s static_mesh read failed: %s" % (c.get_name(), exc))
            try:
                mat = c.get_material(0)
            except Exception:  # noqa: BLE001
                mat = None
            try:
                vis = c.is_visible()
            except Exception:  # noqa: BLE001
                vis = "?"
            log("   %-18s mesh=%-32s slot0=%-26s vis=%s" % (
                c.get_name(), mesh.get_name() if mesh else "None",
                mat.get_name() if mat else "None", vis))

# 存档里的构件（面板摆下的喷泉会记在 Prefabs 里）
saves = sorted(glob.glob(os.path.join(unreal.Paths.convert_relative_path_to_full(
    unreal.Paths.project_saved_dir()), "SaveGames", "Voxel20_*.sav")), key=os.path.getmtime, reverse=True)
log("voxel saves: %d" % len(saves))
for s in saves[:3]:
    log("   %s  %.1f KB  %s" % (os.path.basename(s), os.path.getsize(s) / 1024.0,
                                unreal.Paths.convert_relative_path_to_full("")))
    try:
        raw = open(s, "rb").read()
        hit = re.findall(rb"[ -~]{4,}", raw)
        interesting = sorted({h.decode("ascii", "ignore") for h in hit
                              if re.search(rb"(fountain|door|window|roman)", h, re.I)})
        log("   构件名命中: %s" % (interesting[:20] if interesting else "(none)"))
    except Exception as exc:  # noqa: BLE001
        log("   read failed: %s" % exc)
log("done")
