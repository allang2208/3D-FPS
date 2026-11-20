"""Build the textured, editable baker and export all of his skinned parts on the R4 rig."""
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from baker_cap import add_baker_cap

PROJECT = HERE.parents[1]
BAKER = PROJECT / "SourceAssets/VillageBaker"
BODY = BAKER / "WardrobeR1/Baker_Body.blend"
OUT = BAKER / "AssemblyR1"


def face_material(name, maps):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    link = material.node_tree.links.new
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .60
    shader.inputs["Specular IOR Level"].default_value = .32
    shader.inputs["Subsurface Weight"].default_value = .045
    shader.inputs["Subsurface Scale"].default_value = .008
    for index, (kind, path) in enumerate(maps.items()):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        node.location = (-620, 360 - index * 240)
        if kind != "BC":
            node.image.colorspace_settings.name = "Non-Color"
        if kind == "N":
            normal = nodes.new("ShaderNodeNormalMap")
            normal.location = (-250, -30)
            link(node.outputs["Color"], normal.inputs["Color"])
            link(normal.outputs["Normal"], shader.inputs["Normal"])
        else:
            socket = {"BC": "Base Color", "R": "Roughness", "M": "Metallic"}[kind]
            link(node.outputs["Color"], shader.inputs[socket])
    return material


def attach_head(rig, source, spec):
    triangles = source["tri"]
    mesh = bpy.data.meshes.new("Baker | bare head, hair and native collar")
    mesh.from_pydata(source["p"].tolist(), [], triangles.tolist())
    mesh.update()
    head = bpy.data.objects.new("SK_VillageBaker_Head", mesh)
    bpy.context.scene.collection.objects.link(head)
    head.parent = rig
    for i, maps in enumerate(spec["materials"]):
        label = "Neck" if i == len(spec["materials"]) - 1 else f"FaceHair_{i}"
        mesh.materials.append(face_material(f"M_VillageBaker_{label}", maps))
    mesh.polygons.foreach_set("material_index", source["m"])
    mesh.polygons.foreach_set("use_smooth", np.ones(len(triangles), dtype=bool))
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", source["uv"].astype("f").ravel())
    mesh.normals_split_custom_set_from_vertices(source["n"].tolist())
    joints, weights = source["joints"], source["weights"]
    rigid = (weights[:, 0] > .99999) & (joints[:, 1] < 0)
    for i in np.unique(joints[joints >= 0]):
        group = head.vertex_groups.new(name=spec["bones"][i])
        ids = np.flatnonzero(rigid & (joints[:, 0] == i)).tolist()
        if ids:
            group.add(ids, 1., "REPLACE")
        rows, cols = np.where((joints == i) & ~rigid[:, None])
        for row, col in zip(rows, cols):
            group.add([int(row)], float(weights[row, col]), "REPLACE")
    armature = head.modifiers.new("Jason R4 head and neck", "ARMATURE")
    armature.object = rig
    head["source"] = spec["fit"]["source_head"]
    return head


def bake_body_build(mesh_object):
    # FBX consumers can load a morph with a default weight of zero. Put the
    # commissioned R4 proportions in the exported base and retain joint morph deltas.
    keys = mesh_object.data.shape_keys
    if not keys or "R4_Build" not in keys.key_blocks:
        return
    build = keys.key_blocks["R4_Build"]
    basis = keys.reference_key
    positions = np.empty(len(basis.data) * 3, dtype=np.float32)
    base = np.empty_like(positions)
    basis.data.foreach_get("co", base)
    build.data.foreach_get("co", positions)
    delta = (positions - base) * build.value
    for key in keys.key_blocks:
        if key != build:
            key.data.foreach_get("co", positions)
            key.data.foreach_set("co", positions + delta)
    # Keep object-mode vertex positions consistent with the new Basis.
    mesh_object.data.vertices.foreach_set("co", base + delta)
    mesh_object.shape_key_remove(build)
    mesh_object.data.update()


def pack_used_materials(objects):
    materials = {slot.material for obj in objects for slot in obj.material_slots if slot.material}
    images = {node.image for mat in materials if mat.use_nodes for node in mat.node_tree.nodes
              if node.type == "TEX_IMAGE" and node.image is not None}
    for image in images:
        if not image.packed_file:
            image.pack()
    return sorted(mat.name for mat in materials), sorted(image.name for image in images)


def apply_export_mask(obj):
    # A general topology modifier would discard shape keys during FBX export.
    # Trim the covered vertices in edit mode to retain the remaining four native morphs.
    mask = obj.modifiers.get("Workwear | conceal covered lower skin")
    if not mask:
        return
    gid = obj.vertex_groups[mask.vertex_group].index
    retained = {v.index for v in obj.data.vertices
                if any(g.group == gid and g.weight > mask.threshold for g in v.groups)}
    obj.modifiers.remove(mask)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in retained], context="VERTS")
    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def fbx_channels(meshes, maps):
    # FBX's material writer follows direct texture nodes. Distribute packed
    # channels here so the cloth and cap carry surface response with their color.
    for mat in {s.material for obj in meshes for s in obj.material_slots if s.material}:
        if not mat.use_nodes:
            continue
        tree = mat.node_tree
        shader = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        packed = next((n for n in tree.nodes if n.type == "TEX_IMAGE" and n.image
                       and Path(n.image.filepath).name in maps), None)
        if not shader or not packed:
            continue
        channels = maps[Path(packed.image.filepath).name]
        for socket, key in (("Roughness", "rough"), ("Metallic", "metal")):
            target = shader.inputs[socket]
            for link in list(target.links):
                tree.links.remove(link)
            if isinstance(channels[key], str):
                node = tree.nodes.new("ShaderNodeTexImage")
                node.image = bpy.data.images.load(channels[key], check_existing=True)
                node.image.colorspace_settings.name = "Non-Color"
                if not node.image.packed_file:
                    node.image.pack()
                tree.links.new(node.outputs["Color"], target)
            else:
                target.default_value = channels[key]


def main():
    work = Path(sys.argv[sys.argv.index("--") + 1])
    spec = json.loads((work / "setup.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BODY))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(obj for obj in scene.objects if obj.type == "ARMATURE" and obj.data.bones.get("head"))
    # The wardrobe includes its own bare collar for authoring without the face.
    # This head contains that same border with a continuous join and matching UVs.
    removed = []
    for obj in list(scene.objects):
        if obj.name in {"Jason_OriginalHead", "Jason_UnchangedHead", "Jason_Original", "Jason_StrongTall_R3_Comparison"} or "Baker_Neck_Base" in obj.name:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    with np.load(work / "head.npz") as source:
        head = attach_head(rig, source, spec)
    cap_parts = add_baker_cap([head], rig)
    meshes = [obj for obj in scene.objects if obj.type == "MESH"
              and any(mod.type == "ARMATURE" and mod.object == rig for mod in obj.modifiers)]
    for obj in meshes:
        if obj.parent != rig:
            world = obj.matrix_world.copy()
            obj.parent = rig
            obj.matrix_world = world
        bake_body_build(obj)
        if obj.get("source_variant") == "Jason StrongTall R4":
            # This donor copied raw UE clockwise faces into Blender. Orient skin
            # outward for the same back-face culling as the authored clothes.
            obj.data.flip_normals()
    bpy.data.orphans_purge(do_recursive=True)
    material_names, image_names = pack_used_materials(meshes)
    scene["character"] = "Village baker | StrongTall R4 | Meshy head with integral hair, separate linen cap"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_distance = 3.15
            space.region_3d.view_location = (0., 0., .95)
            from mathutils import Vector
            space.region_3d.view_rotation = Vector((0., -1., -.025)).to_track_quat("-Z", "Y")
            space.shading.color_type = "TEXTURE"
            space.overlay.show_overlays = False
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    blend = OUT / "VillageBaker_R1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), relative_remap=True, compress=True)
    # Unreal's FBX importer treats the designated armature object as the container
    # above the actual native root bone. All wearable meshes have the same parent.
    rig.name = "Armature"
    rig.hide_set(False)
    rig.hide_viewport = False
    for obj in meshes:
        apply_export_mask(obj)
    fbx_channels(meshes, spec["fbx_maps"])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [rig, *meshes]:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.context.view_layer.update()
    fbx = OUT / "SK_VillageBaker_R1.fbx"
    result = bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={"ARMATURE", "MESH"},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z", axis_up="Y", primary_bone_axis="X", secondary_bone_axis="-Y",
        add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=True, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=True, use_custom_props=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX exporter returned {result}")
    record = dict(spec["fit"], editable=blend.name, skeletal_fbx=fbx.name,
                  native_bones=len(rig.data.bones), removed_donor_objects=removed,
                  fitted_head=head.name, separate_cap=[obj.name for obj in cap_parts],
                  mesh_parts=[obj.name for obj in meshes], material_slots=material_names,
                  packed_images=image_names, animation_exported=False)
    (OUT / "geometry_ready.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print("BAKER_ASSEMBLY_SAVED", blend.name, fbx.name, flush=True)


if __name__ == "__main__":
    main()
