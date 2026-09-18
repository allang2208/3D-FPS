"""只读核对：调色板里的窗条目、窗类入口、两个网格资产（不写任何资产）。

运行：UnrealEditor-Cmd.exe <uproject> -run=pythonscript -Script=<abs> -unattended -nop4 -nosplash -NullRHI
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
DIR = "/Game/Props/Window20260918"


def log(m):
    print("[wv] " + m)


pal = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
log("palette=%s components=%d materials=%s" % (
    pal is not None, len(pal.get_editor_property("components") or []),
    [str(m.get_editor_property("id")) for m in (pal.get_editor_property("materials") or [])]))
for e in pal.get_editor_property("components") or []:
    entry_id = str(e.get_editor_property("id"))
    if not entry_id.startswith("window"):
        continue
    mesh = e.get_editor_property("mesh")
    surf = e.get_editor_property("surface")
    actor = e.get_editor_property("actor_class")
    log("entry %-14s cells=%s group=%-7s mesh=%-20s actor=%-18s surface=%s" % (
        entry_id, str(e.get_editor_property("footprint")), str(e.get_editor_property("material")),
        mesh.get_name() if mesh else "None", actor.get_name() if actor else "None",
        surf.get_name() if surf else "None"))

cls = unreal.load_class(None, "/Script/FPSGAME.ColdSteelWindow")
log("class=%s" % (cls.get_name() if cls else None))
if cls:
    names = [n for n in dir(cls) if "Window" in n or "Door" in n or "Configure" in n]
    log("入口/方法: %s" % ", ".join(sorted(names)))

for name in ("SM_WindowFrame_100", "SM_WindowLeaf_100"):
    asset = unreal.EditorAssetLibrary.load_asset(DIR + "/" + name) or unreal.load_asset(DIR + "/" + name)
    if not asset:
        log("%s MISSING" % name)
        continue
    bb = asset.get_bounds()
    per_slot = [asset.get_material(i) for i in range(asset.get_num_materials(0) if hasattr(asset, "get_num_materials") else 1)]
    slot_names = [m.get_name() if m else "None" for m in per_slot]
    log("%-20s bbox %.1f x %.1f x %.1f origin=(%.1f, %.1f, %.1f) tris=%d slots=%s" % (
        name, bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        bb.origin.x, bb.origin.y, bb.origin.z, asset.get_num_triangles(0), slot_names))
    try:
        body = asset.get_editor_property("body_setup")
        shapes = len(body.get_editor_property("agg_geom").get_editor_property("convex_elems"))
        boxes = len(body.get_editor_property("agg_geom").get_editor_property("box_elems"))
        log("    collision: convex=%d box=%d" % (shapes, boxes))
    except Exception as exc:  # noqa: BLE001
        log("    collision 读取失败: %s" % exc)
log("done")
