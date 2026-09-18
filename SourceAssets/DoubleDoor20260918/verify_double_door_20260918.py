"""只读核对：调色板里的双开门条目、门类、两个门网格资产、以及体素块物品（不写任何资产）。

运行：UnrealEditor-Cmd.exe <uproject> -run=pythonscript -Script=<abs> -unattended -nop4 -nosplash -NullRHI
"""

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
DIR = "/Game/Props/DoubleDoor20260918"
DIR1 = "/Game/Props/SingleDoor20260918"


def log(m):
    print("[dv] " + m)


pal = unreal.EditorAssetLibrary.load_asset(PALETTE) or unreal.load_asset(PALETTE)
components = pal.get_editor_property("components") or []
log("palette=%s components=%d materials=%s" % (
    pal is not None, len(components),
    [str(m.get_editor_property("id")) for m in (pal.get_editor_property("materials") or [])]))
for e in components:
    entry_id = str(e.get_editor_property("id"))
    if not (entry_id.startswith(("double_door", "window", "door"))):
        continue
    mesh = e.get_editor_property("mesh")
    surf = e.get_editor_property("surface")
    actor = e.get_editor_property("actor_class")
    log("entry %-20s cells=%s group=%-7s mesh=%-22s actor=%-22s surface=%s" % (
        entry_id, str(e.get_editor_property("footprint")), str(e.get_editor_property("material")),
        mesh.get_name() if mesh else "None", actor.get_name() if actor else "None",
        surf.get_name() if surf else "None"))

cls = unreal.load_class(None, "/Script/FPSGAME.ColdSteelDoubleDoor")
log("class=%s（父类看 C++：AColdSteelWindow）" % (cls.get_name() if cls else "None"))

for name in ("SM_DoubleDoorFrame_200", "SM_DoubleDoorLeaf_200", "SM_SingleDoorFrame_100", "SM_SingleDoorLeaf_100"):
    path = (DIR1 + "/" + name) if name.startswith("SM_SingleDoor") else (DIR + "/" + name)
    asset = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
    if not asset:
        log("%s MISSING" % name)
        continue
    bb = asset.get_bounds()
    body = asset.get_editor_property("body_setup")
    geom = body.get_editor_property("agg_geom")
    log("%-24s bbox %.1f x %.1f x %.1f origin=(%.1f, %.1f, %.1f) tris=%d box=%d convex=%d" % (
        name, bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2,
        bb.origin.x, bb.origin.y, bb.origin.z, asset.get_num_triangles(0),
        len(geom.get_editor_property("box_elems")), len(geom.get_editor_property("convex_elems"))))
log("done")
