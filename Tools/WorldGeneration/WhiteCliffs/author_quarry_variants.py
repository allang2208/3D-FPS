"""Cut the project's two closed quarry scans and separate the six Fab limestone stones."""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/HillsLandscapeRepair20261117/SolidScansR9"
OUTPUT = PROJECT / "SourceAssets/HillsQuarryRockLayout20261119"
OUTPUT.mkdir(parents=True, exist_ok=True)
records = []


def bounds(points):
    return tuple(Vector([fn(p[i] for p in points) for i in range(3)]) for fn in (min, max))


def export(obj, name, source, material):
    bpy.context.view_layer.update()
    lo, hi = bounds([obj.matrix_world @ v.co for v in obj.data.vertices])
    # Keep scan axes and UVs. Place the pivot at the centre of the footprint.
    transform = obj.matrix_world.copy()
    transform.translation -= Vector(((hi.x + lo.x) / 2, (hi.y + lo.y) / 2, lo.z))
    obj.matrix_world = transform
    obj.name = name
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(OUTPUT / (name + ".fbx")), use_selection=True,
                             object_types={"MESH"}, axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", use_tspace=True, bake_anim=False)
    records.append(dict(name=name, source=str(source), material=material,
                        size_cm=[round(n * 100, 2) for n in hi - lo]))


def fracture(label, name, planes):
    source = SOURCE / (label + ".blend")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    mesh = obj.data
    cut_slot = next(i for i, m in enumerate(mesh.materials) if "LimestoneCut" in m.name)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv = bm.loops.layers.uv.active
    lo, hi = bounds([v.co for v in bm.verts])
    for direction, fraction in planes:
        normal = Vector(direction).normalized()
        origin = Vector([lo[i] + (hi[i] - lo[i]) * fraction[i] for i in range(3)])
        bmesh.ops.bisect_plane(bm, geom=[*bm.verts, *bm.edges, *bm.faces],
                               plane_co=origin, plane_no=normal, dist=1.e-6, clear_outer=True)
        boundary = [e for e in bm.edges if e.is_boundary]
        if not boundary:
            raise RuntimeError(f"{name} cut did not intersect the solid")
        fill = bmesh.ops.triangle_fill(bm, edges=boundary, normal=normal, use_beauty=True)
        axis = normal.cross(Vector((0, 0, 1))).normalized()
        other = normal.cross(axis)
        for face in fill["geom"]:
            if not isinstance(face, bmesh.types.BMFace):
                continue
            face.material_index = cut_slot
            face.smooth = False
            for loop in face.loops:
                p = loop.vert.co - origin
                loop[uv].uv = (p.dot(axis), p.dot(other))
        if any(not e.is_manifold for e in bm.edges):
            raise RuntimeError(f"{name} has an open fracture surface")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    export(obj, "SM_Quarry" + name, source, label)


fracture("CliffA", "SplitSpur", [((1, .29, .28), (.57, .50, .53))])
fracture("CliffB", "BeddedShelf", [((-.83, .51, .32), (.31, .47, .50))])
fracture("CliffA", "FallenWedge", [((-.75, -.24, .68), (.40, .50, .57)),
                                 ((.89, .31, .19), (.75, .48, .52))])

pack = PROJECT.parent / "VaultCache/FabLibrary/Small_Limestone_Rocks_Pack-09676e2a/Extracted"
source = next(pack.glob("*_High.fbx"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(source))
stones = sorted((o for o in bpy.context.scene.objects if o.type == "MESH"), key=lambda o: o.name)
if len(stones) != 6:
    raise RuntimeError(f"Expected six individual limestone scans, found {len(stones)}")
for i, stone in enumerate(stones, 1):
    export(stone, f"SM_QuarryChip{i:02}", source, "LimestoneSpoil")
(OUTPUT / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf8")
