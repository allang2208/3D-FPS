"""把青铜火把注册成建造构件（壁挂件）。

  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/add_torch_prefab_20260918.py

前提：`VoxelBuildPalette.h` 的 `EVoxelPrefabMount` / `FVoxelBuildPrefab::Mount` 必须已经**全量编译**
（带资产的 USTRUCT 不能用热补丁改），否则写资产会丢字段。

口径（20 cm 格）：
  - 占格 3 × 2 × 5 = 60 × 40 × 100 cm（火把本体 50.5 × 33 × 86.6 cm，尾椎尖到杯唇）。
  - 摆放采用"逻辑构件"分支：锚点 = 占格底面中心，构件自己往上搭。
  - `ActorOffsetCm = (-51, 0, 44)`：把 actor 原点沿贴墙法线往墙里挪 51 cm（杆根 x=16 因此嵌进墙面 5 cm、
    杯心离墙面 29 cm），并在竖直方向抬 44 cm 让尾椎贴占格底面。
  - `PivotOffsetCm = (-9.75, 0, 0)`：幽灵预览与落地必须同一口径（预览用的是包围盒公式）。
  - `Mount = Wall`：只能贴竖直表面放置，朝向跟随表面法线，且不参与"失去支撑脱落"。

幂等：按 Id 就地更新，不动调色板里其它条目。
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
D = "/Game/Props/RomanColumn20260915"
ID = "bronze_torch"


def log(m):
    print("[torch_prefab] " + m)


palette = unreal.EditorAssetLibrary.load_asset(PALETTE)
if not palette:
    raise RuntimeError("active palette missing: %s" % PALETTE)
mesh = unreal.EditorAssetLibrary.load_asset(D + "/SM_BronzeTorch")
surface = unreal.EditorAssetLibrary.load_asset(D + "/M_Bronze")
logic_class = unreal.load_class(None, "/Script/FPSGAME.BronzeTorch")
if not mesh or not surface or not logic_class:
    raise RuntimeError("assets missing: mesh=%s surface=%s class=%s" % (bool(mesh), bool(surface), bool(logic_class)))

entry = unreal.VoxelBuildPrefab()
entry.set_editor_property("id", ID)
entry.set_editor_property("display_name", unreal.Text("青铜火把 · 贴墙"))
entry.set_editor_property("mesh", mesh)
entry.set_editor_property("footprint", unreal.IntVector(3, 2, 5))
entry.set_editor_property("mount", unreal.VoxelPrefabMount.WALL)
entry.set_editor_property("surface", surface)
entry.set_editor_property("pivot_offset_cm", unreal.Vector(-9.75, 0.0, 0.0))
entry.set_editor_property("actor_class", logic_class)
entry.set_editor_property("actor_offset_cm", unreal.Vector(-51.0, 0.0, 44.0))
entry.set_editor_property("material", "marble")

components = list(palette.get_editor_property("components"))
before = len(components)
replaced = False
for index, existing in enumerate(components):
    if existing.get_editor_property("id") == ID:
        components[index] = entry
        replaced = True
        break
if not replaced:
    components.append(entry)
palette.set_editor_property("components", components)
log("components %d -> %d (replaced=%s)" % (before, len(components), replaced))
log("saved=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False))

back = unreal.EditorAssetLibrary.load_asset(PALETTE).get_editor_property("components")
for item in back:
    if item.get_editor_property("id") == ID:
        log("read back: %s | %s | %s cells | mount=%s | actor=%s | actorOffset=%s" % (
            item.get_editor_property("id"), str(item.get_editor_property("display_name")),
            item.get_editor_property("footprint"), item.get_editor_property("mount"),
            item.get_editor_property("actor_class"), item.get_editor_property("actor_offset_cm")))
log("total prefabs now: %d" % len(back))
log("DONE")
