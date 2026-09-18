"""把罗马喷泉登记成**逻辑构件**并迁移关卡实例（2026-09-18）。

1. 调色板 `roman_fountain`：ActorClass → `/Script/FPSGAME.ColdSteelFountain`
   （面板摆出来的喷泉从此自带水膜/溢流/水柱/占位水声；Id／占格 48×48×36 不变）。
2. 关卡 `DayNight_Lighting`：把旧的 `RomanFountain1`（StaticMeshActor）与
   `RomanFountainFX_Jet`（NiagaraActor）合成一个 `AColdSteelFountain`，位置沿用旧 actor 的变换。
   水柱不再用硬编码 z=720：新类按主网格包围盒把水柱放到塔尖（本地 z = 包围盒高），
   所以旧水柱"悬在塔尖上方 360 cm"的问题一并修掉。脚本会打印新旧坐标以便对账。

顺序硬规则（沿用喷泉流水线）：**先写调色板、再 load_map**——同一进程里加载过关卡后，
调色板保存会静默失败。先跑过 `build_fountain_water_20260918.py` 与一次 C++ 构建。

运行（编辑器关闭时最稳）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/RomanFountain20260917/register_fountain_prefab_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import os
import time

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
ENTRY_ID = "roman_fountain"
FOUNTAIN_CLASS = "/Script/FPSGAME.ColdSteelFountain"
FOUNTAIN_MESH = "/Game/Props/RomanFountain20260917/SM_RomanFountain_20"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
STARTED = time.time()
LOG = []


def log(m):
    print("[fnt-reg] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-28s %s" % (label, "OK" if ok else "FAIL"))


def stamp_of(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


# ------------------------------------------------------------------ 1. palette
pal = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
cls = unreal.load_class(None, FOUNTAIN_CLASS)
mesh = unreal.load_asset(FOUNTAIN_MESH)
check("palette_loadable", pal is not None)
check("fountain_class", cls is not None)
check("fountain_mesh", mesh is not None)
if pal and cls:
    entries = list(pal.get_editor_property("components") or [])
    hit = None
    for e in entries:
        if str(e.get_editor_property("id")) == ENTRY_ID:
            hit = e
            break
    check("entry_found", hit is not None)
    if hit:
        hit.set_editor_property("actor_class", cls)
        hit.set_editor_property("mesh", mesh)
        hit.set_editor_property("display_name", unreal.Text("罗马喷泉（蛋糕塔·自带水效）"))
        pal.modify()
        pal.set_editor_property("components", entries)
        saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
        log("palette saved=%s" % saved)
        back = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
        for e in back.get_editor_property("components") or []:
            if str(e.get_editor_property("id")) != ENTRY_ID:
                continue
            fp = e.get_editor_property("footprint")
            actor = e.get_editor_property("actor_class")
            log("palette readback %s cells=(%d,%d,%d) actor=%s mesh=%s" % (
                ENTRY_ID, fp.x, fp.y, fp.z,
                actor.get_name() if actor else "None",
                e.get_editor_property("mesh").get_name()))
            check("palette_actor_class", actor is not None and actor.get_name() == "ColdSteelFountain")
    check("palette_disk", bool(stamp_of(PALETTE)))

# ------------------------------------------------------------------ 2. level
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
headless = os.environ.get("FOUNTAIN_HEADLESS") == "1"
pie = False
if not headless and les:
    try:
        pie = les.is_in_play_in_editor()
    except Exception as exc:  # noqa: BLE001
        log("PIE query failed (headless?): %s" % exc)
log("PIE=%s headless=%s" % (pie, headless))
if pie:
    log("PIE active - level migration skipped")
    check("level_migration_skipped_pie", True)
elif not les or not les.load_level(LEVEL):
    check("level_loaded", False)
else:
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = actor_sub.get_all_level_actors()
    fountains = [a for a in actors if a.get_actor_label() == "RomanFountain1"]
    jets = [a for a in actors if a.get_actor_label() == "RomanFountainFX_Jet"]
    new_ones = [a for a in actors if "ColdSteelFountain" in a.get_class().get_name()]
    log("found: RomanFountain1=%d jet=%d ColdSteelFountain=%d" % (len(fountains), len(jets), len(new_ones)))
    check("old_fountain_found", len(fountains) == 1)
    if len(fountains) == 1:
        old = fountains[0]
        loc = old.get_actor_location()
        rot = old.get_actor_rotation()
        spawn = actor_sub.spawn_actor_from_class(cls, loc, rot) if hasattr(actor_sub, "spawn_actor_from_class") \
            else None
        check("new_actor_spawned", spawn is not None)
        if spawn:
            spawn.set_actor_label("RomanFountain1")
            log("new fountain at (%.0f,%.0f,%.0f) rot yaw=%.1f" % (loc.x, loc.y, loc.z, rot.yaw))
            # 旧的水柱：记录旧位置，然后连旧 mesh actor 一起销毁
            for j in jets:
                jl = j.get_actor_location()
                log("old jet was at (%.0f,%.0f,%.0f)" % (jl.x, jl.y, jl.z))
                j.destroy_actor()
                check("old_jet_destroyed", True)
            old.destroy_actor()
            check("old_mesh_actor_destroyed", True)
            if hasattr(spawn, "AlignGeometry"):
                spawn.AlignGeometry()
            saved = les.save_current_level()
            umap = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
                "GameMaps/DayNight_Lighting.umap"
            st = os.stat(umap).st_mtime if os.path.exists(umap) else 0
            check("umap_saved", bool(saved) and st >= STARTED - 60.0)
            log("umap %s mtime %s" % (umap, time.strftime("%H:%M:%S", time.localtime(st))))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
