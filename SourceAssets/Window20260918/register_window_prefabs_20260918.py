"""把 100×100 双开窗登记为建造构件（逻辑构件路径，照 add_door_prefab_entries_20260917.py）。

窗分三档材质，分别归到调色板的木材／石头／大理石栏：条目 `Material` 填对应材质 ID，
`ActorClass` 指向 `/Script/FPSGAME.ColdSteelWindow`，`Mesh` 只做抽屉缩略图与预览 ghost。

运行（编辑器必须关闭；先做过全量 BuildEditor，否则 load_class 找不到窗类）：
  UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
      -Script=D:/FPS3D/FPSGAME/SourceAssets/Window20260918/register_window_prefabs_20260918.py \
      -unattended -nop4 -nosplash -NullRHI -nosound -abslog=<日志>
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
FRAME_MESH = "/Game/Props/Window20260918/SM_WindowFrame_100"
WINDOW_CLASS = "/Script/FPSGAME.ColdSteelWindow"
# 窗框 20×100×100 cm → 占格 (1,5,5)；洞口 88×88，两扇 43.5 宽对开（每扇带一个圆把手）。
CELLS = (1, 5, 5)
ENTRIES = [
    ("window_wood", "木窗（E 键开关·100×100）", "/Game/Building/Voxels/Rounded/M_Voxel_Wood", "wood"),
    ("window_stone", "石窗（E 键开关·100×100）", "/Game/Building/Voxels/Rounded/M_Voxel_Stone", "stone"),
    ("window_marble", "大理石窗（E 键开关·100×100）", "/Game/Props/RomanColumn20260915/M_RomanStone_V2", "marble"),
]


def log(message):
    print("[window-prefab] " + message)


def size_of(path):
    mesh = unreal.load_asset(path)
    if not mesh:
        return None
    extent = mesh.get_bounds().box_extent
    return (round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1))


frame_size = size_of(FRAME_MESH)
got = tuple(int(round(v / 20.0)) for v in frame_size) if frame_size else None
log("SM_WindowFrame_100=%s 占格=%s 期望=%s %s" % (
    frame_size, got, CELLS, "OK" if got == CELLS else "MISMATCH"))

palette = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
if not palette:
    raise RuntimeError("palette not loadable")
frame_mesh = unreal.load_asset(FRAME_MESH)
actor_class = unreal.load_class(None, WINDOW_CLASS)
log("window class=%s frame mesh=%s" % (actor_class.get_name() if actor_class else None,
                                       frame_mesh.get_name() if frame_mesh else None))
if not actor_class or not frame_mesh:
    raise RuntimeError("窗类或窗框网格缺失：先跑 Build-Editor.ps1 与 build_window_meshes_20260918.py")

entries = list(palette.get_editor_property("components") or [])
log("components before=%d" % len(entries))
for entry_id, caption, surface_path, group in ENTRIES:
    surface = unreal.load_asset(surface_path)
    if not surface:
        log("SKIP %s: surface missing (%s)" % (entry_id, surface_path))
        continue
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", entry_id)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("mesh", frame_mesh)
    entry.set_editor_property("surface", surface)
    entry.set_editor_property("footprint", unreal.IntVector(CELLS[0], CELLS[1], CELLS[2]))
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entry.set_editor_property("material", unreal.Name(group))
    entry.set_editor_property("actor_class", actor_class)
    entry.set_editor_property("actor_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entries = [e for e in entries if str(e.get_editor_property("id")) != entry_id]
    entries.append(entry)
    log("entry %-14s cells=%s class=%s group=%s surface=%s" % (
        entry_id, CELLS, actor_class.get_name(), group, surface.get_name()))

palette.modify()
palette.set_editor_property("components", entries)
saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
log("saved=%s" % saved)

back = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
for entry in back.get_editor_property("components") or []:
    mesh = entry.get_editor_property("mesh")
    actor = entry.get_editor_property("actor_class")
    log("readback %-16s cells=%s group=%-7s mesh=%s actor=%s" % (
        str(entry.get_editor_property("id")), str(entry.get_editor_property("footprint")),
        str(entry.get_editor_property("material")),
        mesh.get_name() if mesh else "None", actor.get_name() if actor else "None"))
log("done")
