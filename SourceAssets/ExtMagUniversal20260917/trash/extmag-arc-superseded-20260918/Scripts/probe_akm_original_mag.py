"""Look for a complete AKM factory magazine (with floor plate) in the original source.

The extracted preview object keeps open boundaries at the magazine's bottom, so
check the pre-extraction source for the plate before authoring anything.
"""
import bpy
import bmesh
from mathutils import Vector

SOURCES = [
    r"D:\FPS3D\FPSGAME\SourceAssets\AKMSoviet20260911\SK_AKM_MannyNative.fbx",
    r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913\AKM\SK_AKM_MannyNative.fbx",
]


def boundary_loops(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
    loops = []
    verts = {v for edge in boundary for v in edge.verts}
    remaining = set(verts)
    while remaining:
        seed = remaining.pop()
        stack, group = [seed], [seed]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                if len(edge.link_faces) != 1:
                    continue
                other = edge.other_vert(current)
                if other in remaining:
                    remaining.discard(other)
                    stack.append(other)
                    group.append(other)
        loops.append(group)
    bm.free()
    return loops


for path in SOURCES:
    print("PROBE3 source", path, flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        if not pts:
            continue
        # Magazine well/bottom region measured from the extracted preview object.
        mag = [p for p in pts if 0.10 < p.y < 0.42 and p.z < -0.19 and p.x < 0.12]
        if not mag:
            continue
        lo = Vector((min(p.x for p in mag), min(p.y for p in mag), min(p.z for p in mag)))
        hi = Vector((max(p.x for p in mag), max(p.y for p in mag), max(p.z for p in mag)))
        print("PROBE3", ob.name, "verts", len(ob.data.vertices), "mag_region_verts", len(mag),
              "lo", tuple(round(v, 4) for v in lo), "hi", tuple(round(v, 4) for v in hi), flush=True)
        loops = boundary_loops(ob)
        near = 0
        for group in loops:
            center = sum((ob.matrix_world @ v.co for v in group), Vector()) / len(group)
            if 0.10 < center.y < 0.42 and center.z < -0.19 and center.x < 0.12:
                near += 1
                print("PROBE3 boundary_loop verts", len(group), "center",
                      tuple(round(v, 4) for v in center), flush=True)
        print("PROBE3 loops_total", len(loops), "loops_in_mag_region", near, flush=True)
print("PROBE3_DONE", flush=True)
