"""Replace Lin Zhi's original head in the full-height, skinned FaceR2 master.

Run with Blender in background mode. Source dimensions use Blender centimetres
after normalization, matching the existing UE skeleton and FBX export settings.
"""
import hashlib
import json
from math import atan2
from pathlib import Path
import struct
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from assemble_neck import Surface, fit
from spectacles import add_spectacles


BODY = HERE.parents[2] / "SourceAssets/VillageHerbalist/FullBody"
DIRECTORY = BODY / "HeadR3/Assembly"
DONOR = BODY / "HeadR3/Meshy/head.glb"
MODEL = "SK_VillageHerbalist_HeadR3"


def normalized_fit(points, rig):
    low, high = np.min(points, axis=0), np.max(points, axis=0)
    height = high[2] - low[2]
    origin = Vector(((high[0] + low[0]) * .5, (high[1] + low[1]) * .5, low[2]))
    # Source sagittal profile landmarks measured on the generated head in units
    # of its full height. The chin is the lowest point anterior to the throat.
    chin_fraction = .19101083
    nose = Vector((-.00089145, -.44220873, .44644008))
    target_chin_z, target_crown_z = 146.624146, 168.
    full_height_cm = (target_crown_z - target_chin_z) / (1. - chin_fraction)
    front = rig.data.bones["headfront"].head_local - rig.data.bones["head"].head_local
    yaw = Matrix.Rotation(atan2(front.x, -front.y), 4, "Z")
    center = Vector((.42440, -11.08898, target_crown_z - full_height_cm))
    rotated_nose = yaw @ (nose * full_height_cm)
    center.x -= rotated_nose.x
    center.y -= rotated_nose.y
    return Matrix.Translation(center) @ yaw @ Matrix.Scale(full_height_cm / height, 4) @ Matrix.Translation(-origin)


def select_only(objects, active):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def bind_fitted_color():
    """Use the neck-matched albedo in the editable master and retain the raw Meshy source."""
    atlas = DIRECTORY / "Materials/T_LinZhiHead_Color.png"
    if not atlas.is_file():
        return
    mat = bpy.data.materials["M_LinZhiHead"]
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    color_node = shader.inputs["Base Color"].links[0].from_node
    if color_node.type != "TEX_IMAGE":
        raise ValueError("Cannot bind the fitted neck atlas to the head color input")
    color_node.image = bpy.data.images.load(str(atlas), check_existing=True)
    color_node.image.pack()


def source_materials():
    with DONOR.open("rb") as f:
        f.seek(12)
        size, kind = struct.unpack("<I4s", f.read(8))
        if kind != b"JSON":
            raise ValueError("Missing GLB asset description")
        doc = json.loads(f.read(size))
    indices = sorted({p.get("material", 0) for m in doc["meshes"] for p in m["primitives"]})
    return [doc["materials"][i].get("name", f"Material_{i}") for i in indices]


def import_head(rig, body):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(DONOR), merge_vertices=True)
    imported = set(bpy.context.scene.objects) - before
    meshes = sorted((o for o in imported if o.type == "MESH"), key=lambda o: o.name)
    containers = [o for o in imported if o.type != "MESH"]
    if not meshes:
        raise ValueError("No head surface in the supplied GLB")
    points = [tuple(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices]
    transform = normalized_fit(points, rig)
    source_names = source_materials()
    source_to_slot = {name: ("M_LinZhiHead" if i == 0 else f"M_LinZhiHead_{i}")
                      for i, name in enumerate(source_names)}
    materials = {m for o in meshes for m in o.data.materials if m}
    if len(materials) == 1 and len(source_names) == 1:
        next(iter(materials)).name = source_to_slot[source_names[0]]
    else:
        for material in materials:
            material.name = source_to_slot[material.name]
    for obj in meshes:
        obj.data.transform(transform @ obj.matrix_world)
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.vertex_groups.clear()
    if len(meshes) > 1:
        select_only(meshes, meshes[0])
        bpy.ops.object.join()
    head = meshes[0]
    head.name = head.data.name = "LinZhi_Head_Hair"
    for o in containers:
        bpy.data.objects.remove(o, do_unlink=True)
    head.parent = rig
    head.matrix_parent_inverse = Matrix.Identity(4)
    for g in body.vertex_groups:
        head.vertex_groups.new(name=g.name)
    armature = head.modifiers.new("Village herbalist skin", "ARMATURE")
    armature.object = rig
    bpy.context.view_layer.update()
    return head, source_to_slot


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BODY / "FaceR2/VillageHerbalist.blend"))
    body, = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    rig = body.find_armature()
    if not rig or body.data.materials[0].name != "M_VillageHerbalist":
        raise ValueError("The full-body source lacks the expected skin or body material")
    body_surface = Surface(body, upper=False)
    head, material_names = import_head(rig, body)
    bind_fitted_color()
    head_surface = Surface(head, upper=True)
    section = fit(body_surface, head_surface)
    body_surface.finish()
    head_surface.finish()
    glasses = add_spectacles([head], rig)
    select_only([rig, body, head, *glasses], rig)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY / "VillageHerbalist_HeadR3.blend"), relative_remap=True)
    fbx = DIRECTORY / (MODEL + ".fbx")
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype="NULL",
        bake_anim=False, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="Y", axis_up="Z", use_mesh_modifiers=False, mesh_smooth_type="FACE",
        path_mode="RELATIVE", embed_textures=False,
    )
    meshes = [body, head, *glasses]
    info = {"fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(), "skeleton": rig.name,
            "bones": len(rig.data.bones), "height_cm": 168., "head_source": "../Meshy/head.glb",
            "source_materials_to_slots": material_names, "seam": section,
            "parts": [{"name": o.name, "vertices": len(o.data.vertices),
                       "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
                       "materials": [mat.name for mat in o.data.materials]} for o in meshes]}
    marker = DIRECTORY / "geometry-ready.json"
    temp = marker.with_suffix(".tmp")
    temp.write_text(json.dumps(info, indent=2), encoding="utf8")
    temp.replace(marker)
    print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
