"""Headless: dump baluster to triangle-soup OBJ via GeometryScript list conversion."""

import unreal

SV = unreal.ModelingService
BALUSTER = "/Game/Props/RomanColumn20260915/SM_RomanBaluster_Small"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917\baluster_v3.obj"

r = SV.load_mesh_from_static_mesh(BALUSTER, 0)
dm = SV.get_dynamic_mesh(getattr(r, "handle", None))
n_vert = dm.get_vertex_count()
n_tri = dm.get_triangle_count()
print("[dump] counts: verts=%d tris=%d closed=%s open_edges=%s comps=%s volume=%s" % (
    n_vert, n_tri, dm.get_is_closed_mesh(), dm.get_num_open_border_edges(),
    dm.get_num_connected_components(), str(dm.get_mesh_volume_area())))

_, tlist, _ = dm.get_all_triangle_i_ds()
tarr = tlist.convert_index_list_to_array()
print("[dump] triangles=%d" % len(tarr))

with open(OUT, "w") as f:
    f.write("# baluster v3 dump (triangle soup)\n")
    fi = 0
    for tid in tarr:
        t = int(tid)
        ok, v1, v2, v3 = dm.get_triangle_positions(t)
        fn, ok2 = dm.get_triangle_face_normal(t)
        fi += 1
        f.write("v %.4f %.4f %.4f\n" % (v1.x, v1.y, v1.z))
        f.write("v %.4f %.4f %.4f\n" % (v2.x, v2.y, v2.z))
        f.write("v %.4f %.4f %.4f\n" % (v3.x, v3.y, v3.z))
        f.write("vn %.4f %.4f %.4f\n" % (fn.x, fn.y, fn.z))
        b = fi * 3 - 2
        f.write("f %d//%d %d//%d %d//%d\n" % (b, fi, b + 1, fi, b + 2, fi))
print("[dump] wrote %s (faces=%d)" % (OUT, n_tri))
