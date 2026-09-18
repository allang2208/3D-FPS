"""Count open edges left by the inserted band (read-only)."""
import bpy
import bmesh
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = ARGV[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bm = bmesh.new()
bm.from_mesh(ob.data)
boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
print("SEAM boundary_edges", len(boundary), "verts", len(ob.data.vertices), flush=True)
if boundary:
    pts = [ob.matrix_world @ v.co for edge in boundary for v in edge.verts]
    print("SEAM bounds", tuple(round(min(p[i] for p in pts), 4) for i in range(3)),
          tuple(round(max(p[i] for p in pts), 4) for i in range(3)), flush=True)
    # Group them by height so the band seams show up as separate clusters.
    heights = sorted(round(p.z, 3) for p in pts)
    clusters = []
    for value in heights:
        if clusters and abs(value - clusters[-1][-1]) < 0.01:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    print("SEAM clusters", [(len(c), round(sum(c) / len(c), 4)) for c in clusters], flush=True)
bm.free()
print("SEAM_DONE", flush=True)
