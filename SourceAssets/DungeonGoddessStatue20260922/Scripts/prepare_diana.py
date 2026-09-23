"""Normalise the raw Diana scan and export the UE import inputs.

Input : Source/source/Diana_C/Diana_C.obj  (photogrammetry master, Z-up world coords,
        base far from origin, 500,726 tris, one 8192x8192 diffuse atlas)
Output: Authored/SM_GoddessStatue_Diana.fbx      game mesh, metres, base at Z=0, pivot on base centre
        Authored/Diana_Editable.blend            editable source with textures packed
        Textures/T_GoddessStatueDiana_BaseColor.png   4096 downscale of the 8192 master
        Receipts/prepare.json                    measured numbers for the record

The model's front faces -Y after this import (verified by rendering the four
orthogonal views: Previews/orientation.jpg). The project FBX convention
(axis_forward='-Y') maps that to +X in UE, so actor yaw controls the facing.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <Diana_C.obj> <case_root> [target_height_m] [texture_size]
"""
import sys
import json
import bpy
from mathutils import Vector

CASE = None
TARGET_H = 2.05
TEX_SIZE = 4096


def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def hard_edge_stats(mesh):
    """Max angle between loop normals sharing a vertex - a faceting canary.

    Blender 5.1 dropped Mesh.calc_normals_split(); corner normals are exposed as
    the read-only mesh.corner_normals collection instead.
    """
    import math
    corners = mesh.corner_normals
    per_vert = {}
    for loop in mesh.loops:
        per_vert.setdefault(loop.vertex_index, []).append(Vector(corners[loop.index].vector))
    worst = 0.0
    for normals in per_vert.values():
        if len(normals) < 2:
            continue
        base = normals[0]
        for n in normals[1:]:
            if base.length and n.length:
                worst = max(worst, base.angle(n))
    return math.degrees(worst)


def main():
    global CASE, TARGET_H, TEX_SIZE
    argv = sys.argv
    args = argv[argv.index("--") + 1:]
    src, CASE = args[0], args[1]
    if len(args) > 2:
        TARGET_H = float(args[2])
    if len(args) > 3:
        TEX_SIZE = int(args[3])

    from pathlib import Path
    root = Path(CASE)
    for sub in ("Authored", "Textures", "Receipts"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    receipt = {"stage": "preparing", "source": src, "unit": "metre", "tests_run": False}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=src, forward_axis='NEGATIVE_Y', up_axis='Z')
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    assert len(meshes) == 1, "expected a single mesh object, got %d" % len(meshes)
    obj = meshes[0]
    obj.name = "SM_GoddessStatue_Diana"
    obj.data.name = "SM_GoddessStatue_Diana"

    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    mn, mx = bbox([obj])
    receipt["source_mesh"] = {
        "tris": tris, "verts": len(obj.data.vertices),
        "bbox_min": [round(v, 4) for v in mn], "bbox_max": [round(v, 4) for v in mx],
        "size": [round(mx[i] - mn[i], 4) for i in range(3)],
        "has_custom_normals": bool(obj.data.has_custom_normals),
        "max_loop_normal_angle_deg": round(hard_edge_stats(obj.data), 2),
    }

    # Uniform scale to the target height, then move the base centre onto the origin.
    height = mx.z - mn.z
    scale = TARGET_H / height
    cx = (mn.x + mx.x) / 2.0
    cy = (mn.y + mx.y) / 2.0
    obj.scale = (scale, scale, scale)
    obj.location = (-cx * scale, -cy * scale, -mn.z * scale)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    mn2, mx2 = bbox([obj])
    receipt["normalised"] = {
        "scale_factor": round(scale, 8),
        "target_height_m": TARGET_H,
        "bbox_min": [round(v, 5) for v in mn2], "bbox_max": [round(v, 5) for v in mx2],
        "size_m": [round(mx2[i] - mn2[i], 5) for i in range(3)],
        "pivot": "base centre, base plane at Z=0",
        "front_axis": "-Y (Blender) -> +X (UE at yaw 0)",
    }

    # Downscale the 8192 master atlas for the game texture; keep the master in Source/.
    images = [i for i in bpy.data.images if i.size[0] > 0]
    assert len(images) == 1, "expected one atlas, got %s" % [i.name for i in images]
    img = images[0]
    receipt["source_texture"] = {"name": img.name, "width": img.size[0], "height": img.size[1]}
    if img.size[0] > TEX_SIZE:
        img.scale(TEX_SIZE, TEX_SIZE)
    out_tex = root / "Textures" / "T_GoddessStatueDiana_BaseColor.png"
    img.filepath_raw = str(out_tex)
    img.file_format = 'PNG'
    img.save()
    img.filepath = str(out_tex)
    img.reload()
    receipt["game_texture"] = {"path": str(out_tex), "width": img.size[0], "height": img.size[1],
                               "note": "8192 master kept in Source/, 4096 used in UE"}

    bpy.ops.file.pack_all()
    blend = root / "Authored" / "Diana_Editable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    receipt["editable_source"] = str(blend)

    fbx = root / "Authored" / "SM_GoddessStatue_Diana.fbx"
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
    receipt["fbx"] = str(fbx)
    receipt["fbx_export"] = {"axis_forward": "-Y", "axis_up": "Z", "mesh_smooth_type": "FACE",
                             "use_tspace": True}
    receipt["stage"] = "exported"
    (root / "Receipts" / "prepare.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("PREPARE_RECEIPT", json.dumps(receipt))


main()
