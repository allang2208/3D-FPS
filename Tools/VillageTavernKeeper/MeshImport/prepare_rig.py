"""Normalize the vendor's skinned body to a 170 cm, ground-origin UE character."""
import json
import math
import re
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT = Path(__file__).resolve().parents[3]
BODY = PROJECT / "SourceAssets/VillageTavernKeeper/FullBody"
OUT = BODY / "UEAuthoringR1"
TEX = BODY / "MeshyR1/Textures"
FBX = BODY / "RigR1/TavernKeeper_Rigged.fbx"
GLB = BODY / "RigR1/TavernKeeper_Rigged.glb"


def read_rig():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if FBX.exists():
        bpy.ops.import_scene.fbx(filepath=str(FBX), use_anim=False, use_image_search=False)
        source = FBX
    else:
        bpy.ops.import_scene.gltf(filepath=str(GLB))
        source = GLB
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one imported armature from {source}, found {len(armatures)}.")
    rig = armatures[0]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.find_armature() == rig]
    if not meshes:
        raise RuntimeError(f"No skinned character mesh was imported from {source}")
    return source, rig, meshes


def bind_world_position(rig, keys):
    for key in keys:
        for bone in rig.data.bones:
            name = re.sub(r"[^a-z0-9]", "", bone.name.lower())
            if name.endswith(key):
                return rig.matrix_world @ bone.head_local
    raise RuntimeError(f"Missing landmark {keys[0]} on {list(rig.data.bones.keys())}")


def editable_surface():
    material = bpy.data.materials.new("TavernKeeperPBR")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    for row, (name, channel) in enumerate([("base_color", "Base Color"), ("normal", "Normal"),
                                          ("roughness", "Roughness"), ("metallic", "Metallic")]):
        image = bpy.data.images.load(str(TEX / ("M0_" + name + ".png")), check_existing=False)
        image.colorspace_settings.name = "sRGB" if name == "base_color" else "Non-Color"
        sample = nodes.new("ShaderNodeTexImage")
        sample.image = image
        sample.location = (-700, 300 - row * 290)
        color = sample.outputs["Color"]
        if channel == "Normal":
            normal = nodes.new("ShaderNodeNormalMap")
            normal.location = (-300, 10)
            links.new(color, normal.inputs["Color"])
            color = normal.outputs["Normal"]
        links.new(color, shader.inputs[channel])
    return material


source_file, rig, meshes = read_rig()
rig.animation_data_clear()
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
world = {obj: obj.matrix_world.copy() for obj in [rig, *meshes]}
low = float("inf")
high = -low
for mesh in meshes:
    for vertex in mesh.data.vertices:
        z = (world[mesh] @ vertex.co).z
        low, high = min(low, z), max(high, z)
left = bind_world_position(rig, ("leftarm", "leftupperarm", "upperarml", "leftshoulder", "leftupleg", "thighl"))
right = bind_world_position(rig, ("rightarm", "rightupperarm", "upperarmr", "rightshoulder", "rightupleg", "thighr"))
ankle_l = bind_world_position(rig, ("leftfoot", "footl", "leftankle", "anklel"))
ankle_r = bind_world_position(rig, ("rightfoot", "footr", "rightankle", "ankler"))
center = (ankle_l + ankle_r) * 0.5
center.z = low
# Facing Blender -Y puts the character's anatomical left on +X. The selected
# FBX basis matches Unreal's import basis, which flips Y to make the scene left-handed.
body_left = left - right
normalization = (Matrix.Scale(170.0 / (high - low), 4)
                 @ Matrix.Rotation(-math.atan2(body_left.y, body_left.x), 4, "Z")
                 @ Matrix.Translation(-center))
rig.parent = None
rig.matrix_world = Matrix.Identity(4)
rig.data.transform(normalization @ world[rig])
rig.name = "Armature"
material = editable_surface()
for index, mesh in enumerate(meshes):
    mesh.animation_data_clear()
    mesh.parent = rig
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.matrix_basis = Matrix.Identity(4)
    mesh.data.transform(normalization @ world[mesh], shape_keys=True)
    mesh.name = "TavernKeeper" if index == 0 else f"TavernKeeper_{index}"
    mesh.data.materials.clear()
    mesh.data.materials.append(material)
    for polygon in mesh.data.polygons:
        polygon.material_index = 0
for other in list(bpy.context.scene.objects):
    if other != rig and other not in meshes:
        bpy.data.objects.remove(other, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.01
rig.data.pose_position = "POSE"
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action="DESELECT")
for obj in [rig, *meshes]:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "TavernKeeper_Rig.blend"), relative_remap=True)
bpy.ops.export_scene.fbx(
    filepath=str(OUT / "SK_TavernKeeper.fbx"), use_selection=True,
    object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, use_armature_deform_only=False,
    armature_nodetype="NULL", bake_anim=False, apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_UNITS", axis_forward="Y", axis_up="Z", use_mesh_modifiers=False,
    path_mode="RELATIVE", embed_textures=False)
(OUT / "rig_preparation.json").write_text(json.dumps({
    "source": str(source_file), "mesh_objects": [mesh.name for mesh in meshes], "bones": len(rig.data.bones),
    "height_cm": 170.0, "up": "+Z", "ue_front": "+Y", "origin": "Ground at ankle midpoint",
    "bone_names": list(rig.data.bones.keys()),
    "source_world_to_cm": [list(row) for row in normalization],
    "textures": {"base_color": "4096x4096", "normal": "4096x4096", "roughness": "2048x2048", "metallic": "2048x2048"},
}, indent=2), encoding="utf-8")
