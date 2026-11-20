"""Normalize the Meshy skin to 168 cm at ground origin, facing UE +Y."""
import json
import math
import re
from pathlib import Path

import bpy
from mathutils import Matrix


ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / "SourceAssets/VillageHerbalist/FullBody"
OUT = BODY / "UEAuthoringR1"
HEIGHT_CM = 168.


def plain(name):
    return re.sub("[^a-z0-9]", "", name.lower())


def landmark(rig, *aliases):
    for alias in aliases:
        for bone in rig.data.bones:
            if plain(bone.name).endswith(alias):
                return rig.matrix_world @ bone.head_local
    raise ValueError("Missing rig landmark " + str(aliases))


def prepare():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = BODY / "RigR1/rigged.glb"
    if source.exists():
        bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
    else:
        source = BODY / "RigR1/rigged.fbx"
        bpy.ops.import_scene.fbx(filepath=str(source), use_anim=False, use_image_search=False)
    scene = bpy.context.scene
    rig, = [o for o in scene.objects if o.type == "ARMATURE"]
    rig.animation_data_clear()
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    meshes = [o for o in scene.objects if o.type == "MESH"]
    world = {o: o.matrix_world.copy() for o in [rig, *meshes]}
    sides = (landmark(rig, "upperarml", "leftarm") - landmark(rig, "upperarmr", "rightarm"))
    center = (landmark(rig, "footl", "leftfoot") + landmark(rig, "footr", "rightfoot")) * .5
    bounds = [min((world[obj] @ v.co).z for v in obj.data.vertices) for obj in meshes]
    center.z = min(bounds)
    top = max(max((world[obj] @ v.co).z for v in obj.data.vertices) for obj in meshes)
    transform = (Matrix.Scale(HEIGHT_CM / (top - center.z), 4)
                 @ Matrix.Rotation(-math.atan2(sides.y, sides.x), 4, "Z") @ Matrix.Translation(-center))
    manifest = json.loads((OUT / "surfaces.json").read_text(encoding="utf-8"))
    slots = {m["source_name"]: m["name"] for m in manifest}
    assigned = {}
    for obj in meshes:
        for material_slot in obj.material_slots:
            mat = material_slot.material
            if mat in assigned:
                continue
            name = re.sub(r"\.\d{3}$", "", mat.name) if mat else ""
            target = slots.get(name, manifest[0]["name"] if len(manifest) == 1 else None)
            if not target:
                raise ValueError(f"Cannot match source surface {name} on {obj.name}")
            assigned[mat] = target
        if obj.parent == rig and obj.parent_type == "BONE":
            bone_name = obj.parent_bone
            group = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
            group.add([v.index for v in obj.data.vertices], 1., "REPLACE")
            modifier = obj.modifiers.new("Meshy rigid attachment", "ARMATURE")
            modifier.object = rig
        elif obj.find_armature() != rig:
            raise ValueError(f"Missing source rig binding for {obj.name}")
        obj.animation_data_clear()
        obj.parent = rig
        obj.parent_type = "OBJECT"
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        obj.data.transform(transform @ world[obj], shape_keys=True)
    for mat, name in assigned.items():
        if mat:
            mat.name = name
    rig.parent = None
    rig.matrix_world = Matrix.Identity(4)
    rig.data.transform(transform @ world[rig])
    rig.name = "Armature"
    for obj in list(scene.objects):
        if obj != rig and obj not in meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = .01
    rig.data.pose_position = "POSE"
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [rig, *meshes]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "VillageHerbalist.blend"), relative_remap=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / "SK_VillageHerbalist.fbx"), use_selection=True,
        object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, use_armature_deform_only=False,
        armature_nodetype="NULL", bake_anim=False, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="Y", axis_up="Z", use_mesh_modifiers=False, mesh_smooth_type="FACE",
        path_mode="RELATIVE", embed_textures=False)
    (OUT / "rig.json").write_text(json.dumps(dict(source=source.name, bones=len(rig.data.bones),
         mesh_objects=[o.name for o in meshes], height_cm=HEIGHT_CM, ue_front="+Y",
         source_to_cm=[list(r) for r in transform]), indent=2), encoding="utf-8")


prepare()
