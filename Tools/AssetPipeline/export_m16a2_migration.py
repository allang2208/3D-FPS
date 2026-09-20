"""Export the legacy M16A2 gun only; no hands, animation or gameplay changes."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "SourceAssets/M16A2Migration20260919"
EXPORT = CASE / "Export"
SOURCE = CASE / "Source/M16A2_Godot_Modular.blend"
PARTS = [
    ("M16Mesh_m16a2_base", "Receiver", "m16a2_base"),
    ("M16Mesh_magazine", "Magazine", "magazine"),
    ("M16Mesh_m16a2_bolt", "Bolt", "m16a2_bolt"),
    ("M16Mesh_m16a2_trigger", "Trigger", "m16a2_trigger"),
    ("M16Mesh_m16a2_boltcatch", "BoltCatch", "m16a2_boltcatch"),
    ("M16Mesh_m16a2_chargehandle", "ChargingHandle", "m16a2_chargehandle"),
    ("M16Mesh_m16a2_chargehandle2", "ChargingHandleLatch", "m16a2_chargehandle2"),
    ("M16Mesh_m16a2_release", "MagazineRelease", "m16a2_release"),
    ("M16Mesh_m16a2_ejection_port_cover", "EjectionPortCover", "m16a2_ejection_port_cover"),
    ("M16FactoryStock", "Stock", "M16FactoryStock"),
    ("M16FactoryGrip", "PistolGrip", "M16FactoryGrip"),
    ("M16FactoryForeend", "Handguard", "M16FactoryForeend"),
    ("M16FactoryMuzzle", "Muzzle", "M16FactoryMuzzle"),
]

bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
scene = bpy.context.scene
source_rig = bpy.data.objects["M16_Mechanism"]
# Bake the basis once into meshes and rest bones: source metres, -Y forward,
# to centimetres, +X forward. UE's KeepXYZAxes import flips only handedness Y.
base_origin = source_rig.matrix_world @ source_rig.data.bones["m16a2_base"].head_local
conversion = Matrix.Scale(100.0, 4) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Translation(-base_origin)
source_bones = {}
for bone in source_rig.data.bones:
    source_bones[bone.name] = {
        "head": conversion @ source_rig.matrix_world @ bone.head_local,
        "tail": conversion @ source_rig.matrix_world @ bone.tail_local,
        "parent": bone.parent.name if bone.parent else "m16a2_base",
    }

meshes = []
for source_name, label, bone_name in PARTS:
    source_obj = bpy.data.objects[source_name]
    data = source_obj.data.copy()
    data.transform(conversion @ source_obj.matrix_world)
    mesh = bpy.data.objects.new("M16A2_" + label, data)
    scene.collection.objects.link(mesh)
    meshes.append(mesh)

for obj in list(scene.objects):
    if obj not in meshes:
        bpy.data.objects.remove(obj, do_unlink=True)

scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.01
scene.unit_settings.length_unit = "CENTIMETERS"
scene.frame_start = scene.frame_end = 1
scene.frame_set(1)

material = bpy.data.materials.new("M_M16A2_PBR")
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
for kind, socket in [("BaseColor", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal"), ("AO", None)]:
    image = bpy.data.images.load(str(CASE / "Textures" / f"m16a2_{kind}.png"), check_existing=False)
    if kind != "BaseColor":
        image.colorspace_settings.name = "Non-Color"
    texture = nodes.new("ShaderNodeTexImage")
    texture.name = "M16A2_" + kind
    texture.image = image
    image.pack()
    if kind == "Normal":
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(texture.outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    elif socket:
        links.new(texture.outputs["Color"], bsdf.inputs[socket])

rig_data = bpy.data.armatures.new("M16A2_MechanicalSkeleton")
rig = bpy.data.objects.new("SK_M16A2_Mechanical", rig_data)
scene.collection.objects.link(rig)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
root = rig_data.edit_bones.new("WPN_Root")
root.head, root.tail = (0, 0, 0), (0, 0, 2.5)
for name, data in source_bones.items():
    bone = rig_data.edit_bones.new(name)
    bone.head, bone.tail = data["head"], data["tail"]
for name, data in source_bones.items():
    parent = "WPN_Root" if name == "m16a2_base" else data["parent"]
    if name == "m16a2_chargehandle2":
        parent = "m16a2_chargehandle"
    rig_data.edit_bones[name].parent = rig_data.edit_bones[parent]

# Furniture is independently addressable; attachment-side origins come from
# authored part geometry, not from independently recentering the complete gun.
for mesh, (source_name, label, bone_name) in zip(meshes, PARTS):
    if bone_name in source_bones:
        continue
    points = [v.co for v in mesh.data.vertices]
    centre_y = (min(v.y for v in points) + max(v.y for v in points)) * 0.5
    centre_z = (min(v.z for v in points) + max(v.z for v in points)) * 0.5
    if label == "Stock":
        head = Vector((max(v.x for v in points), centre_y, centre_z))
    elif label == "PistolGrip":
        head = Vector(((min(v.x for v in points) + max(v.x for v in points)) * 0.5, centre_y, max(v.z for v in points)))
    else:
        head = Vector((min(v.x for v in points), centre_y, centre_z))
    bone = rig_data.edit_bones.new(bone_name)
    bone.head, bone.tail = head, head + Vector((0, 0, 2.5))
    bone.parent = rig_data.edit_bones["m16a2_base"]
bpy.ops.object.mode_set(mode="OBJECT")

for mesh, (_, _, bone_name) in zip(meshes, PARTS):
    mesh.data.materials.clear()
    mesh.data.materials.append(material)
    mesh.parent = rig
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.matrix_basis = Matrix.Identity(4)
    mesh.vertex_groups.new(name=bone_name).add(list(range(len(mesh.data.vertices))), 1.0, "REPLACE")
    modifier = mesh.modifiers.new("MechanicalRig", "ARMATURE")
    modifier.object = rig

def export_fbx(path, objects, skeletal=False):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig if skeletal else objects[0]
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True,
        object_types={"MESH", "ARMATURE"} if skeletal else {"MESH"},
        axis_forward="Y", axis_up="Z", global_scale=1.0,
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
        add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=False, mesh_smooth_type="FACE", use_tspace=False,
        use_mesh_modifiers=not skeletal, path_mode="AUTO",
    )

(EXPORT / "Parts").mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(CASE / "M16A2_Mechanical_Editable.blend"))
export_fbx(EXPORT / "SK_M16A2_Mechanical.fbx", [rig] + meshes, skeletal=True)
export_fbx(EXPORT / "SM_M16A2_Assembled.fbx", meshes)

parts_manifest = []
for mesh, (source_name, label, bone_name) in zip(meshes, PARTS):
    pivot = rig.data.bones[bone_name].head_local.copy()
    part_mesh = mesh.data.copy()
    part_mesh.transform(Matrix.Translation(-pivot))
    part = bpy.data.objects.new("SM_M16A2_" + label, part_mesh)
    scene.collection.objects.link(part)
    export_fbx(EXPORT / "Parts" / f"SM_M16A2_{label}.fbx", [part])
    parts_manifest.append({
        "name": label, "legacy_object": source_name, "bone": bone_name,
        "asset": f"/Game/Weapons/M16A2Migration/Parts/SM_M16A2_{label}",
        "assembly_location_cm": [pivot.x, -pivot.y, pivot.z],
        "assembly_rotation_degrees": [0, 0, 0],
        "vertices": len(part_mesh.vertices),
        "triangles": sum(len(p.vertices) - 2 for p in part_mesh.polygons),
    })
    bpy.data.objects.remove(part, do_unlink=True)

manifest = {
    "source": str(SOURCE), "scope": "gun geometry, PBR, mechanical rig and separate parts only",
    "axes": "UE centimetres, +X muzzle, +Z up; FBX import KeepXYZAxes",
    "source_origin_metres": list(base_origin),
    "parts": parts_manifest,
    "bones": [{"name": b.name, "parent": b.parent.name if b.parent else None,
               "head_cm": [b.head_local.x, -b.head_local.y, b.head_local.z]} for b in rig.data.bones],
    "textures": {i.name: list(i.size) for i in bpy.data.images if i.name.startswith("m16a2_") and i.packed_file},
    "testing": "Not performed; no render, PIE or gameplay integration requested.",
}
(CASE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("M16A2_EXPORT_COMPLETE " + json.dumps({"parts": len(parts_manifest), "bones": len(rig.data.bones), "triangles": sum(p["triangles"] for p in parts_manifest)}))
