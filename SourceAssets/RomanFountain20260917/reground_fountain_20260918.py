"""把关卡里的喷泉**贴地**（只改这一个 actor 的 z，然后保存关卡）。

根因（`probe_level_ground_20260918.py` 的读数）：
  Floor（500 m 地面）顶面 z=0，`MarbleFloor_Colonnade` z=[0..20]，凉亭 `RomanPavilion2_*` 都在 z=0/20；
  而 `RomanFountain1` 在 **z=−360**、包围盒 z=[−361..360] —— 整座喷泉沉进地面 3.6 m，
  大盆与它的水面全在地下，画面只剩上半截"蛋糕塔"，于是既像固体、水柱又相对可见塔尖偏高。

正确口径：喷泉网格 pivot 在**底面**（包围盒 origin_z=360＝高度一半），Actor 的 z 应等于地面顶面 z；
`AColdSteelFountain::AlignGeometry()` 会把网格包围盒底面放到 Actor 原点，所以 **Actor z = 地面 z**。
脚本按关卡里名字含 `Floor` 的静态网格 actor 的**包围盒顶面**取地面高度（不写死数字），并做一次包围盒相交检查。

运行（编辑器必须关闭；关卡文件会被占用）：
  $env:FOUNTAIN_HEADLESS='1'; UnrealEditor-Cmd.exe <uproject> -run=pythonscript -Script=<本文件> ...
"""

import os
import time

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
GROUND_HINT = "Floor"
GROUND_Z_OVERRIDE = None   # 需要时填数字强制地面高度


def log(m):
    print("[reground] " + m)


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not les:
    raise RuntimeError("LevelEditorSubsystem 不可用")
headless = os.environ.get("FOUNTAIN_HEADLESS") == "1"
if not headless:
    try:
        if les.is_in_play_in_editor():
            log("PIE active - abort")
            raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        pass
if not les.load_level(LEVEL):
    raise RuntimeError("load_level failed")

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_sub.get_all_level_actors()
fountains = [a for a in actors if "ColdSteelFountain" in a.get_class().get_name()]
log("fountains=%d" % len(fountains))

ground_z = GROUND_Z_OVERRIDE
ground_actor = None
if ground_z is None:
    # 只认 **XY 范围包含喷泉** 的地面（关卡里既有 500 m 大地面，也有凉亭那块抬高的大理石台基；
    # 直接取"最高"会选到 2100 cm 外、根本不在脚下的台基）。同 XY 内取最高的那个面。
    fx = fy = None
    if fountains:
        fl = fountains[0].get_actor_location()
        fx, fy = fl.x, fl.y
    cands = []
    for a in actors:
        label = a.get_actor_label() or ""
        if not ("StaticMesh" in a.get_class().get_name()):
            continue
        o, e = a.get_actor_bounds(False)
        if fx is not None and not (abs(o.x - fx) <= e.x and abs(o.y - fy) <= e.y):
            continue
        if GROUND_HINT in label or "Floor" in label:
            cands.append((label, o.z + e.z))
    log("ground candidates: %s" % cands)
    if cands:
        ground_z = max(z for _, z in cands)
        ground_actor = [a for a in actors if (a.get_actor_label() or "") ==
                        [n for n, z in cands if z == ground_z][0]]
if ground_z is None:
    raise RuntimeError("找不到地面 actor；可给 GROUND_Z_OVERRIDE 填数字")
log("ground_z=%.1f" % ground_z)

for f in fountains:
    old = f.get_actor_location()
    new = unreal.Vector(old.x, old.y, ground_z)
    if abs(old.z - new.z) < 0.5:
        log("%s already grounded at z=%.1f" % (f.get_actor_label(), old.z))
        continue
    o, e = f.get_actor_bounds(False)
    span = (new.x - e.x, new.x + e.x, new.y - e.y, new.y + e.y, new.z - e.z, new.z + e.z)
    clash = None
    for a in actors:
        if a == f or a.get_attach_parent_actor() == f:
            continue
        if ground_actor and a in ground_actor:
            continue      # 地面本身必然"相交"，不算 clash
        if "ColdSteelFountain" in a.get_class().get_name():
            continue
        ao, ae = a.get_actor_bounds(False)
        b = (ao.x - ae.x, ao.x + ae.x, ao.y - ae.y, ao.y + ae.y, ao.z - ae.z, ao.z + ae.z)
        if (b[0] < span[1] and b[1] > span[0] and b[2] < span[3] and b[3] > span[2]
                and b[4] < span[5] and b[5] > span[4]):
            clash = a.get_actor_label() or a.get_name()
            break
    log("move %s: z %.1f -> %.1f, clash=%s" % (f.get_actor_label(), old.z, new.z, clash or "none"))
    f.set_actor_location(new, False, True)
    o2, e2 = f.get_actor_bounds(False)
    log("after: loc z=%.1f bounds z=[%.1f..%.1f]" % (
        f.get_actor_location().z, o2.z - e2.z, o2.z + e2.z))

started = time.time()
saved = les.save_current_level()
umap = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
    "GameMaps/DayNight_Lighting.umap"
st = os.stat(umap).st_mtime if os.path.exists(umap) else 0
log("save=%s umap mtime=%s fresh=%s" % (
    saved, time.strftime("%H:%M:%S", time.localtime(st)), st >= started - 60.0))
log("done")
