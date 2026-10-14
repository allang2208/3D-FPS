"""登记 2026-10-04 门族新构件到建造调色板（编辑器桥 PythonScript 通道）。

- door_physics（铁门·撞开）：ActorClass 从 Fab 物理门 BP_PhysicsDoor_C 换为原生
  ColdSteelContactDoor（透缝+联机一并解决），缩略图网格换补缝门扇。
- 新增：door_key（键门）、key_pickup（门钥匙拾取物）、door_slide（滑动门）、
  door_drag（拖拽门）、door_revolving（旋转门）。软类路径在本编辑器会话里
  尚未加载（需重启编辑器生效），但属性字符串写入不受影响。
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
ASSET = PALETTE + ".DA_VoxelBuildPalette"
LEAF_MESH = "/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40.SM_SingleDoorLeaf_D40"
FRAME_MESH = "/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40.SM_SingleDoorFrame_D40"

palette = unreal.load_asset(ASSET)
if not palette:
    raise RuntimeError("palette load failed: " + ASSET)

components = palette.get_editor_property("Components")

def find(cid):
    for c in components:
        if str(c.get_editor_property("Id")) == cid:
            return c
    return None

wood = find("door_wood")
surface = wood.get_editor_property("Surface") if wood else unreal.SoftObjectPath()

# 1) door_physics 改原生接触门
iron = find("door_physics")
if iron:
    iron.set_editor_property("ActorClass", unreal.load_class(None, "/Script/FPSGAME.ColdSteelContactDoor"))
    iron.set_editor_property("Mesh", unreal.load_object(None, LEAF_MESH))
    iron.set_editor_property("DisplayName", unreal.Text("铁门（撞开）"))
    unreal.log_warning("[DoorPrefabs] door_physics -> ColdSteelContactDoor")

# 2) 新增五件（已存在则跳过）
NEW = [
    ("door_key", "键门（需钥匙）", "/Script/FPSGAME.ColdSteelKeyDoor", LEAF_MESH, (2, 6, 12)),
    ("key_pickup", "门钥匙", "/Script/FPSGAME.ColdSteelKeyPickup", "/Engine/BasicShapes/Cube.Cube", (1, 1, 1)),
    ("door_slide", "滑动门（双扇对滑）", "/Script/FPSGAME.ColdSteelSlidingDoor", LEAF_MESH, (2, 6, 12)),
    ("door_drag", "拖拽门（任意开角）", "/Script/FPSGAME.ColdSteelDragDoor", LEAF_MESH, (2, 6, 12)),
    ("door_revolving", "旋转门（三扇）", "/Script/FPSGAME.ColdSteelRevolvingDoor", LEAF_MESH, (5, 5, 12)),
]
changed = iron is not None
for cid, label, cls, mesh, foot in NEW:
    if find(cid):
        unreal.log_warning("[DoorPrefabs] 已存在，跳过 " + cid)
        continue
    e = unreal.VoxelBuildPrefab()
    e.set_editor_property("Id", unreal.Name(cid))
    e.set_editor_property("DisplayName", unreal.Text(label))
    e.set_editor_property("Mesh", unreal.load_object(None, mesh))
    e.set_editor_property("Footprint", unreal.IntVector(foot[0], foot[1], foot[2]))
    e.set_editor_property("Mount", unreal.VoxelPrefabMount.FREE)
    e.set_editor_property("Surface", surface)
    e.set_editor_property("ActorClass", unreal.load_class(None, cls))
    e.set_editor_property("Material", unreal.Name("wood"))
    components.append(e)
    changed = True
    unreal.log_warning("[DoorPrefabs] 新增 " + cid)

if changed:
    palette.set_editor_property("Components", components)
    ok = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False)
    unreal.log_warning(f"[DoorPrefabs] 调色板保存={ok}")

total = len(palette.get_editor_property("Components"))
ids = [str(c.get_editor_property("Id")) for c in palette.get_editor_property("Components")
       if "door" in str(c.get_editor_property("Id")) or "key" in str(c.get_editor_property("Id"))]
print("DOOR_IDS", ids, "total", total)
