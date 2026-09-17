"""Headless: dump the current pavilion pieces to triangle-soup OBJ for offline analysis."""

import unreal

SV = unreal.ModelingService
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
PIECES = {
    "domev2": "/Game/Props/RomanColumn20260915/SM_RomanPavilionDome_20",

    "ring": "/Game/Props/RomanColumn20260915/SM_PavilionRing_20",
    "stylobate": "/Game/Props/RomanColumn20260915/SM_PavilionStylobate_20",
}


def dump(name, path):
    r = SV.load_mesh_from_static_mesh(path, 0)
    dm = SV.get_dynamic_mesh(getattr(r, "handle", None))
    print("[dump] %s verts=%d tris=%d closed=%s open=%s comps=%s" % (
        name, dm.get_vertex_count(), dm.get_triangle_count(), dm.get_is_closed_mesh(),
        dm.get_num_open_border_edges(), dm.get_num_connected_components()))
    _, tlist, _ = dm.get_all_triangle_i_ds()
    tarr = tlist.convert_index_list_to_array()
    out = OUT_DIR + "\\" + name + ".obj"
    with open(out, "w") as f:
        f.write("# %s\n" % path)
        fi = 0
        for tid in tarr:
            ok, v1, v2, v3 = dm.get_triangle_positions(int(tid))
            fn, _ = dm.get_triangle_face_normal(int(tid))
            fi += 1
            for v in (v1, v2, v3):
                f.write("v %.4f %.4f %.4f\n" % (v.x, v.y, v.z))
            f.write("vn %.4f %.4f %.4f\n" % (fn.x, fn.y, fn.z))
            b = fi * 3 - 2
            f.write("f %d//%d %d//%d %d//%d\n" % (b, fi, b + 1, fi, b + 2, fi))
    print("[dump] wrote %s faces=%d" % (out, fi))


for n, p in PIECES.items():
    dump(n, p)
print("[dump] RESULT: DONE")
