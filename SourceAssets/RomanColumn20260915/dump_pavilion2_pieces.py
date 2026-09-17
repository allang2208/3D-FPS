"""Headless: dump the v2 pavilion pieces (and one column) to triangle-soup OBJ for rendering."""

import unreal

SV = unreal.ModelingService
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
PIECES = {
    "p2_base": "/Game/Props/RomanColumn20260915/SM_RomanPavilionBase_20",
    "p2_arch": "/Game/Props/RomanColumn20260915/SM_RomanPavilionArch_20",
    "p2_dome": "/Game/Props/RomanColumn20260915/SM_RomanPavilionDome_20",
    "p2_column": "/Game/Props/RomanColumn20260915/SM_RomanColumn_Detailed",
    "p2_old_dome": "/Game/Props/RomanColumn20260915/SM_PavilionDome_20",
}


def dump(name, path):
    loaded = SV.load_mesh_from_static_mesh(path, 0)
    handle = getattr(loaded, "handle", None)
    if not handle:
        print("[d2] %s: LOAD FAILED" % name)
        return
    dm = SV.get_dynamic_mesh(handle)
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
    print("[d2] %-12s %6d faces -> %s" % (name, fi, out.split("\\")[-1]))
    SV.release_mesh(handle)


for n, p in PIECES.items():
    dump(n, p)
print("[d2] RESULT: DONE")
