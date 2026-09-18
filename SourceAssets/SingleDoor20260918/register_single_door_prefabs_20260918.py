"""把单扇门的调色板条目同步到当前门框尺寸（占格）与当前门板网格。

调色板 `door_wood`／`door_stone`／`door_marble` 三条：
  - `Mesh`（抽屉缩略图＋预览 ghost）→ 本工程烘焙版门板 `SM_SingleDoorLeaf_D40`；
  - `Footprint` → **按门框包围盒逐轴 /20 向上取整**（2026-09-18 第四轮：40 × 114 × 240 → **(2,6,12)**）。
其余字段（Id／显示名／ActorClass／Surface／Material 分组／偏移）原样保留，只读改写 `Components`。

运行（编辑器必须关闭；先跑过 bake_single_door_meshes_20260918.py）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/SingleDoor20260918/register_single_door_prefabs_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
FRAME_MESH = "/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40"
LEAF_MESH = "/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40"
IDS = ("door_wood", "door_stone", "door_marble")


def log(m):
    print("[single-door-prefab] " + m)


palette = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
frame = unreal.EditorAssetLibrary.load_asset(FRAME_MESH) or unreal.load_asset(FRAME_MESH)
leaf = unreal.EditorAssetLibrary.load_asset(LEAF_MESH) or unreal.load_asset(LEAF_MESH)
if not palette or not frame or not leaf:
    raise RuntimeError("调色板／门框／门板缺失：先跑 bake_single_door_meshes_20260918.py")

extent = frame.get_bounds().box_extent
size = (extent.x * 2.0, extent.y * 2.0, extent.z * 2.0)
cells = tuple(max(1, int((v + 19.9) // 20)) for v in size)
leaf_extent = leaf.get_bounds().box_extent
log("门框 %.2f × %.2f × %.2f → 占格 %s；门板 %.2f × %.2f × %.2f" % (
    size[0], size[1], size[2], cells,
    leaf_extent.x * 2, leaf_extent.y * 2, leaf_extent.z * 2))

entries = list(palette.get_editor_property("components") or [])
hit = 0
for entry in entries:
    if str(entry.get_editor_property("id")) not in IDS:
        continue
    before = entry.get_editor_property("footprint")
    entry.set_editor_property("mesh", leaf)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    hit += 1
    log("entry %-12s cells %s → %s（Mesh → %s）" % (
        str(entry.get_editor_property("id")), (before.x, before.y, before.z), cells, leaf.get_name()))
if hit != len(IDS):
    raise RuntimeError("只找到 %d 条门条目（期望 %d）" % (hit, len(IDS)))

palette.modify()
palette.set_editor_property("components", entries)
saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
log("saved=%s" % saved)

back = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
for entry in back.get_editor_property("components") or []:
    entry_id = str(entry.get_editor_property("id"))
    if entry_id not in IDS:
        continue
    fp = entry.get_editor_property("footprint")
    mesh = entry.get_editor_property("mesh")
    log("readback %-12s cells=(%d,%d,%d) mesh=%s actor=%s" % (
        entry_id, fp.x, fp.y, fp.z, mesh.get_name() if mesh else "None",
        str(entry.get_editor_property("actor_class"))))
log("done")
