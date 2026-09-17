# 只读补充检查：调色板条目的中文名称（按码位打印，绕开控制台代码页）与资产类型／可渲染数据。

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"


def log(message):
    print("[panel-audit-text] " + message)


def codes(text):
    return " ".join("U+%04X" % ord(ch) for ch in text)


palette = unreal.EditorAssetLibrary.load_asset(ACTIVE) or unreal.load_asset(ACTIVE)
log("palette loadable=%s" % (palette is not None))

for entry in palette.get_editor_property("materials") or []:
    surface = entry.get_editor_property("surface")
    mesh = entry.get_editor_property("example_mesh")
    log("material %-7s caption=[%s] codes=%s" % (
        str(entry.get_editor_property("id")), str(entry.get_editor_property("display_name")),
        codes(str(entry.get_editor_property("display_name")))))
    log("   surface class=%s path=%s" % (
        surface.get_class().get_name() if surface else None,
        surface.get_path_name().split(".")[0] if surface else None))
    log("   mesh class=%s bounds_extent=%s" % (
        mesh.get_class().get_name() if mesh else None,
        tuple(round(v * 2, 1) for v in (mesh.get_bounds().box_extent.x, mesh.get_bounds().box_extent.y,
                                        mesh.get_bounds().box_extent.z)) if mesh else None))

for entry in palette.get_editor_property("components") or []:
    mesh = entry.get_editor_property("mesh")
    surface = entry.get_editor_property("surface")
    log("component %-15s caption=[%s] codes=%s" % (
        str(entry.get_editor_property("id")), str(entry.get_editor_property("display_name")),
        codes(str(entry.get_editor_property("display_name")))))
    log("   mesh class=%s surface class=%s" % (
        mesh.get_class().get_name() if mesh else None,
        surface.get_class().get_name() if surface else None))
    try:
        log("   mesh lod_count=%s triangles_lod0=%s" % (
            mesh.get_num_lods(), mesh.get_num_triangles(0)))
    except Exception as exc:
        log("   mesh lod/triangle query unavailable: %s" % exc)

log("done")
