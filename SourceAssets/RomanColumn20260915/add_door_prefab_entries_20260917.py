# 把迁入的两扇门登记为建造构件（C）：ActorClass 走逻辑构件路径，Mesh 只做抽屉缩略图。
# 运行：UnrealEditor-Cmd <uproject> -run=pythonscript -Script=<abs> -unattended -nop4 -nosplash -NullRHI

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
DOOR_MESH = "/Game/DoorSystem/Demo/StarterContent/Props/SM_Door"
FRAME_MESH = "/Game/DoorSystem/Demo/StarterContent/Props/SM_DoorFrame"
DOOR_MAT = "/Game/DoorSystem/Demo/StarterContent/Props/Materials/M_Door"
FRAME_MAT = "/Game/DoorSystem/Demo/StarterContent/Props/Materials/M_Frame"
# id, caption, actor class, surface（门板＋门框整体材质）, material group
ENTRIES = [
    # 本工程自己的门：不依赖包的角色，E 键直接开关；每种体素一扇，材质与那栏材料一致。
    ("door_wood", "木门（E 键开关）", "/Script/FPSGAME.ColdSteelDoor",
     "/Game/Building/Voxels/Rounded/M_Voxel_Wood", "wood"),
    ("door_stone", "石门（E 键开关）", "/Script/FPSGAME.ColdSteelDoor",
     "/Game/Building/Voxels/Rounded/M_Voxel_Stone", "stone"),
    ("door_marble", "大理石门（E 键开关）", "/Script/FPSGAME.ColdSteelDoor",
     "/Game/Props/RomanColumn20260915/M_RomanStone_V2", "marble"),
    # 包的物理门：靠身体撞开，不需要角色接口，可以直接用；归到「其他」分类（group 留空）。
    ("door_physics", "铁门（撞开）", "/Game/DoorSystem/Blueprints/Doors/BP_PhysicsDoor.BP_PhysicsDoor_C",
     "/Game/DoorSystem/Demo/StarterContent/Props/Materials/M_Door", ""),
]
# 包的交互门（BP_AutoDoor 等）写死了它自己的角色，实测按 E 打不开，先从调色板撤掉。
REMOVE = ["door_auto"]


def log(message):
    unreal.log("[door-prefab] " + message)


def size_of(path):
    mesh = unreal.load_asset(path)
    if not mesh:
        return None
    extent = mesh.get_bounds().box_extent
    return (round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1))


door_size = size_of(DOOR_MESH)
frame_size = size_of(FRAME_MESH)
log("SM_Door=%s  SM_DoorFrame=%s" % (door_size, frame_size))
base = frame_size or door_size or (100.0, 20.0, 200.0)
# 占格向上取整到 20 cm 格，门框含在占格里。
cells = tuple(max(1, int((value + 19.9) // 20)) for value in base)
log("footprint cells=%s" % (cells,))

palette = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
if not palette:
    raise RuntimeError("palette not loadable")
door_mesh = unreal.load_asset(DOOR_MESH)
door_mat = unreal.load_asset(DOOR_MAT)
entries = list(palette.get_editor_property("components") or [])
log("components before=%d" % len(entries))
for drop in REMOVE:
    keep = [e for e in entries if str(e.get_editor_property("id")) != drop]
    if len(keep) != len(entries):
        log("removed %s" % drop)
    entries = keep

for entry_id, caption, class_path, surface_path, group in ENTRIES:
    actor_class = unreal.load_class(None, class_path)
    if not actor_class:
        log("SKIP %s: actor class missing (%s)" % (entry_id, class_path))
        continue
    surface = unreal.load_asset(surface_path)
    if not surface:
        log("SKIP %s: surface missing (%s)" % (entry_id, surface_path))
        continue
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", entry_id)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("mesh", door_mesh)
    entry.set_editor_property("surface", surface)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    # 空 group = 只在「其他」分类出现；填了材质 ID 就只出现在该材质的「其他构造」里。
    entry.set_editor_property("material", unreal.Name(group) if group else unreal.Name("None"))
    entry.set_editor_property("actor_class", actor_class)
    entry.set_editor_property("actor_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entries = [e for e in entries if str(e.get_editor_property("id")) != entry_id]
    entries.append(entry)
    log("entry %-14s cells=%s class=%s group=%s surface=%s" % (
        entry_id, cells, actor_class.get_name(), group, surface.get_name()))

palette.modify()
palette.set_editor_property("components", entries)
saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
log("saved=%s" % saved)

back = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
for entry in back.get_editor_property("components") or []:
    mesh = entry.get_editor_property("mesh")
    actor_class = entry.get_editor_property("actor_class")
    log("readback %-16s cells=%s group=%s mesh=%s actor=%s" % (
        str(entry.get_editor_property("id")),
        str(entry.get_editor_property("footprint")),
        str(entry.get_editor_property("material")),
        mesh.get_name() if mesh else "None",
        actor_class.get_name() if actor_class else "None"))
log("done")
