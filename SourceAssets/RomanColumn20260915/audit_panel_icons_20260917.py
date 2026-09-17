# 建造面板缩略图输入盘点（只读，不写资产、不存档）。
# 核对活动调色板 Rounded/DA_VoxelBuildPalette 的材质与构件：
# 1) Surface 是否指向标准资产且资产存在；2) 条目字段是否写全（Id/DisplayName/Surface/ExampleMesh；
# 构件还要 Mesh/Footprint/Pivot/归属材质）；3) 构件占格是否等于网格包围盒；4) 出图输入是否齐全。
# 依据 Docs/Building/voxel-build-workflow.md 第 6 节修复清单。
# 运行：
#   UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -script=<abs path> -unattended -nop4 -nosplash -NullRHI

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
V = "/Game/Building/Voxels/Rounded"
P = "/Game/Props/RomanColumn20260915"

# id -> (caption, surface, example mesh, physics override)
STANDARD_MATERIALS = {
    "wood": ("木材", V + "/M_Voxel_Wood", V + "/SM_Voxel20_Wood", None),
    "stone": ("石头", V + "/M_Voxel_Stone", V + "/SM_Voxel20_Stone", None),
    "marble": ("大理石", P + "/M_RomanStone_V2", V + "/SM_Voxel20_Stone",
               (2600.0, 3000000.0, 450000.0, 40000.0, 500.0, 15.0)),
}
# id -> (caption, mesh, cells, surface, 归属材质)
STANDARD_COMPONENTS = {
    "roman_column": ("罗马柱", P + "/SM_RomanColumn_Detailed", (4, 4, 13), P + "/M_RomanStone_V2", "marble"),
    "baluster_small": ("矮栏杆罗马柱", P + "/SM_RomanBaluster_Small", (2, 2, 5), P + "/M_Plaster_Detailed", "stone"),
}
DEFAULT_MESH = {"wood": V + "/SM_Voxel20_Wood"}
SHAPES = ("单格", "1 平方米地块", "1 平方米墙面", "1x5 水平直线", "1x5 垂直直线")


def log(message):
    print("[panel-audit] " + message)


def exists(path):
    if not path:
        return False
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            return True
    except Exception:
        pass
    # 远程执行上下文里 EditorAssetLibrary 有时返回 False／不可用，直接按资产路径加载复核。
    try:
        return unreal.load_asset(path) is not None
    except Exception:
        return False


def asset_path(obj):
    if not obj:
        return None
    try:
        return obj.get_path_name().split(".")[0]
    except Exception:
        return str(obj)


def size_of(mesh):
    ext = mesh.get_bounds().box_extent
    return (round(ext.x * 2, 1), round(ext.y * 2, 1), round(ext.z * 2, 1))


def ok(flag_ok):
    return "OK" if flag_ok else "DEVIATION"


issues = []
# 远程执行上下文里 EditorAssetLibrary.load_asset 可能返回 None，按项目既有脚本的做法回退到 load_asset。
palette = unreal.EditorAssetLibrary.load_asset(ACTIVE) or unreal.load_asset(ACTIVE)
log("palette=%s loadable=%s" % (ACTIVE, palette is not None))
if not palette:
    raise RuntimeError("palette not loadable: %s" % ACTIVE)

materials = list(palette.get_editor_property("materials") or [])
material_ids = [str(e.get_editor_property("id")) for e in materials]
log("materials=%d ids=%s" % (len(materials), material_ids))
for entry in materials:
    eid = str(entry.get_editor_property("id"))
    caption = str(entry.get_editor_property("display_name"))
    surface = asset_path(entry.get_editor_property("surface"))
    example = asset_path(entry.get_editor_property("example_mesh"))
    supports = entry.get_editor_property("supports_weight")
    override = entry.get_editor_property("override_physics")
    ph = entry.get_editor_property("physics")
    values = (ph.get_editor_property("density_kg_m3"), ph.get_editor_property("compression_pa"),
              ph.get_editor_property("tension_pa"), ph.get_editor_property("shear_pa"),
              ph.get_editor_property("durability"), ph.get_editor_property("joules_per_damage"))
    log("material id=%-7s caption=%-5s weight=%s" % (eid, caption, supports))
    log("   surface=%-52s exists=%s" % (surface, exists(surface)))
    log("   example=%-52s exists=%s" % (example, exists(example)))
    log("   override_physics=%s values=%s" % (override, values))
    want = STANDARD_MATERIALS.get(eid)
    if want is None:
        issues.append("material '%s' 不在标准表里" % eid)
        continue
    if caption != want[0]:
        issues.append("material '%s' 名称 '%s' != 标准 '%s'" % (eid, caption, want[0]))
    if surface != want[1]:
        issues.append("material '%s' surface %s != 标准 %s" % (eid, surface, want[1]))
    if example != want[2]:
        issues.append("material '%s' example mesh %s != 标准 %s" % (eid, example, want[2]))
    if not exists(surface):
        issues.append("material '%s' surface 资产不存在：%s" % (eid, surface))
    if not exists(example):
        issues.append("material '%s' example mesh 资产不存在：%s" % (eid, example))
    icon_mesh = example if example else DEFAULT_MESH.get(eid, V + "/SM_Voxel20_Stone")
    can_draw = exists(icon_mesh) and exists(surface)
    log("   icon mesh=%s(exists=%s) -> 材质行 shape:%s:-1 + 5 形状 shape:%s:0..4  %s" % (
        icon_mesh, exists(icon_mesh), eid, eid, ok(can_draw)))
    if not can_draw:
        issues.append("material '%s' 出图输入不完整（缺网格或缺材质）" % eid)
    if want[3]:
        if not override:
            issues.append("material '%s' 缺 physics override（标准 %s）" % (eid, want[3]))
        elif tuple(values) != tuple(want[3]):
            issues.append("material '%s' physics override %s != 标准 %s" % (eid, tuple(values), want[3]))

components = list(palette.get_editor_property("components") or [])
log("components=%d" % len(components))
component_ids = []
for entry in components:
    cid = str(entry.get_editor_property("id"))
    component_ids.append(cid)
    caption = str(entry.get_editor_property("display_name"))
    mesh_path = asset_path(entry.get_editor_property("mesh"))
    mesh = entry.get_editor_property("mesh")
    surface = asset_path(entry.get_editor_property("surface"))
    fp = entry.get_editor_property("footprint")
    pivot = entry.get_editor_property("pivot_offset_cm")
    group = str(entry.get_editor_property("material"))
    cells = (fp.x, fp.y, fp.z)
    actual = size_of(mesh) if mesh else None
    expect = tuple(float(c * 20) for c in cells)
    log("component id=%-15s caption=%-8s group=%s" % (cid, caption, group or "(空→只在「其他」)"))
    log("   mesh=%-52s exists=%s" % (mesh_path, exists(mesh_path)))
    log("   surface=%-52s exists=%s" % (surface, exists(surface)))
    log("   cells=%s pivot=%s mesh_size=%s expected=%s %s" % (
        cells, (pivot.x, pivot.y, pivot.z), actual, expect, ok(actual == expect) if actual else "NO MESH"))
    want = STANDARD_COMPONENTS.get(cid)
    if want is None:
        issues.append("component '%s' 不在标准表里" % cid)
    else:
        if caption != want[0]:
            issues.append("component '%s' 名称 '%s' != 标准 '%s'" % (cid, caption, want[0]))
        if mesh_path != want[1]:
            issues.append("component '%s' mesh %s != 标准 %s" % (cid, mesh_path, want[1]))
        if cells != want[2]:
            issues.append("component '%s' 占格 %s != 标准 %s" % (cid, cells, want[2]))
        if surface != want[3]:
            issues.append("component '%s' surface %s != 标准 %s" % (cid, surface, want[3]))
        if group != want[4]:
            issues.append("component '%s' 归属 '%s' != 标准 '%s'" % (cid, group, want[4]))
    if not exists(mesh_path):
        issues.append("component '%s' mesh 资产不存在 → 没有缩略图" % cid)
    elif actual != expect:
        issues.append("component '%s' 网格尺寸 %s != 占格 %s（放置会与 20 cm 网格错位）" % (cid, actual, expect))
    if not exists(surface):
        issues.append("component '%s' surface 资产不存在 → 缩略图用网格默认材质" % cid)
    if group and group not in material_ids:
        issues.append("component '%s' 归属材质 '%s' 不在 Materials 里 → 不会出现在任何材质的「其他构造」" % (cid, group))

for need in STANDARD_MATERIALS:
    if need not in material_ids:
        issues.append("Materials 缺材质 '%s'" % need)
for need in STANDARD_COMPONENTS:
    if need not in component_ids:
        issues.append("Components 缺构件 '%s'" % need)

preview = asset_path(palette.get_editor_property("preview_material"))
log("preview_material=%s exists=%s edge_radius_cm=%s" % (
    preview, exists(preview), palette.get_editor_property("edge_radius_cm")))
if not exists(preview):
    issues.append("preview_material 不存在：%s" % preview)

for mid in material_ids:
    owned = [cid for cid, e in zip(component_ids, components) if str(e.get_editor_property("material")) == mid]
    log("材质 '%s' 的「其他构造」= 5 形状 %s + 同材质构件 %s" % (mid, SHAPES, owned or "(无)"))
    for cid in owned:
        log("   构件卡片 %s 键=piece:%s" % (cid, cid))

log("issues=%d" % len(issues))
for item in issues:
    log("  ! " + item)
log("audit done")
