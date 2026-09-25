"""Save editable hunt-glove meshes; UE imports native bindings without FBX."""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1"
SOURCES = PROJECT / "SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources"
OUT = ROOT / "Editable"
OUT.mkdir(parents=True, exist_ok=True)
reflection = Matrix.Diagonal((1, -1, 1))

for entry in json.loads((ROOT / "manifest.json").read_text()):
    name = entry["profile"]
    data = json.loads(Path(entry["authored"]).read_text())
    native = json.loads((SOURCES / f"{name}.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = bpy.data.armatures.new(name + "_NativeReference")
    rig = bpy.data.objects.new(name + "_NativeReference", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    names = {b["index"]: n for n, b in native["bones"].items()}
    for n, b in native["bones"].items():
        bone = arm.edit_bones.new(n)
        axes = Matrix(b["axes"]).transposed()
        for col in range(3):
            axes.col[col] = axes.col[col].normalized()
        matrix = (reflection @ axes @ reflection).to_4x4()
        matrix.translation = reflection @ Vector(b["position"]) * 0.01
        bone.matrix = matrix
        bone.length = 0.025
    for n, b in native["bones"].items():
        if b["parent"] in names:
            arm.edit_bones[n].parent = arm.edit_bones[names[b["parent"]]]
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh = bpy.data.meshes.new(name + "_HuntFieldGlovesV1")
    mesh.from_pydata([(p[0] * 0.01, -p[1] * 0.01, p[2] * 0.01) for p in data["positions"]], [], data["triangles"])
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = rig
    mod = obj.modifiers.new("NativeBinding", "ARMATURE")
    mod.object = rig
    for n in sorted({n for w in data["weights"] for n in w}):
        obj.vertex_groups.new(name=n)
    for vi, weights in enumerate(data["weights"]):
        for n, w in weights.items():
            obj.vertex_groups[n].add([vi], w, "REPLACE")
    mat = bpy.data.materials.new("HuntLeather_Authoring")
    mat.diffuse_color = (0.18, 0.085, 0.035, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = mat.diffuse_color
    bsdf.inputs["Roughness"].default_value = 0.72
    mesh.materials.append(mat)
    layer = mesh.uv_layers.new(name="Leather")
    split_normals = []
    for face, uv, normals in zip(mesh.polygons, data["uv"], data["normals"]):
        face.use_smooth = True
        for loop, (uu, vv), nrm in zip(face.loop_indices, uv, normals):
            layer.data[loop].uv = (uu, 1 - vv)
            split_normals.append((nrm[0], -nrm[1], nrm[2]))
    mesh.normals_split_custom_set(split_normals)
    obj["UE_source"] = data["source"]
    obj["Contract"] = data["contract"]
    obj["Units"] = "metres; native UE source in centimetres; Y reflected"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"{name}_HuntFieldGlovesV1.blend"))
    print("HUNT_GLOVES_BLEND_SAVED", name, flush=True)
