"""独立进程读回：门框/门板磁盘几何与调色板占格（2026-09-19 宽 120 统一轮）。

只读不写。预期：门框 40.00 × 120.00 × 240.00（三轴整格，与占格 (2,6,12) 完全一致），
门板 18.48 × 94.74 × 226.42（Y=洞口 90×120/113.99、Z=200×240/212），槽数 1/2。
"""
import unreal

FRAME = "/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40"
LEAF = "/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"

def log(m):
    print("[verify-door-grid] " + m)

ok = True
frame = unreal.EditorAssetLibrary.load_asset(FRAME)
leaf = unreal.EditorAssetLibrary.load_asset(LEAF)
fb, lb = frame.get_bounds(), leaf.get_bounds()
fsize = (round(fb.box_extent.x * 2, 2), round(fb.box_extent.y * 2, 2), round(fb.box_extent.z * 2, 2))
lsize = (round(lb.box_extent.x * 2, 2), round(lb.box_extent.y * 2, 2), round(lb.box_extent.z * 2, 2))
log("frame bbox %s tris=%d slots=%d" % (fsize, frame.get_num_triangles(0),
    len(frame.get_editor_property("static_materials") or [])))
log("leaf  bbox %s tris=%d slots=%d" % (lsize, leaf.get_num_triangles(0),
    len(leaf.get_editor_property("static_materials") or [])))
expect_f, expect_l = (40.0, 120.0, 240.0), (18.48, 94.74, 226.42)
for label, got, want in (("frame", fsize, expect_f), ("leaf", lsize, expect_l)):
    good = all(abs(got[i] - want[i]) < 0.05 for i in range(3))
    log("%s %s (expect %s): %s" % (label, "OK" if good else "MISMATCH", want, got))
    ok = ok and good
body = frame.get_editor_property("body_setup")
log("frame collision_trace_flag=%s（环状：应为复杂面碰撞）" % body.get_editor_property("collision_trace_flag"))

pal = unreal.EditorAssetLibrary.load_asset(PALETTE)
for e in pal.get_editor_property("components") or []:
    fid = str(e.get_editor_property("id"))
    if fid in ("door_wood", "door_stone", "door_marble"):
        fp = e.get_editor_property("footprint")
        good = (fp.x, fp.y, fp.z) == (2, 6, 12)
        log("palette %s footprint=(%d,%d,%d) %s" % (fid, fp.x, fp.y, fp.z, "OK" if good else "MISMATCH"))
        ok = ok and good
print("[verify-door-grid] RESULT: " + ("PASS" if ok else "CHECK"))
