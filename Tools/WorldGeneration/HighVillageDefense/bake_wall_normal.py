"""Transfer the full-resolution Meshy wall relief to its UV-preserving game mesh in Blender."""
import hashlib
import json
import os
from pathlib import Path

import bpy


DESIGN = Path(__file__).resolve().parents[3] / "SourceAssets/HillsVillageHighWall20261120/Design01"


def load_wall(path):
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one wall mesh in {path}, found {len(meshes)}")
    return meshes[0]


def bake():
    original = DESIGN / "Meshy/A_HighWall/model.glb"
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    cache = Path(os.environ.get("HIGH_VILLAGE_CACHE", "F:/FPSGAMEData/Caches/Authoring/HighVillageDefense/Reduced"))
    reduced = cache / f"A_HighWall-{digest[:12]}-65000.glb"
    output = DESIGN / "Authored/Bakes"
    output.mkdir(parents=True, exist_ok=True)
    target = output / "HighWallStone_normal.png"
    receipt_path = output / "wall-normal.json"
    receipt = {"original_sha256": digest, "reduced_sha256": hashlib.sha256(reduced.read_bytes()).hexdigest(),
               "mesh_role": "HighWallStone", "texture": target.name, "tangent_convention": "glTF OpenGL"}
    if target.is_file() and receipt_path.is_file() and json.loads(receipt_path.read_text(encoding="utf-8")) == receipt:
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    high = load_wall(original)
    low = load_wall(reduced)
    image = bpy.data.images.new("HighWallStone_Relief", width=2048, height=2048, alpha=False)
    image.colorspace_settings.name = "Non-Color"
    for material in low.data.materials:
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        material.node_tree.nodes.active = node

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    # Both GLBs have the same native basis. Keep projection rays well inside the
    # scan's 0.11-unit thickness, so they cannot pick up stones on the far face.
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_selected_to_active=True,
                        cage_extrusion=0.004, max_ray_distance=0.014, margin=4,
                        normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
    pending = target.with_suffix(".partial.png")
    image.filepath_raw = str(pending)
    image.file_format = "PNG"
    image.save()
    pending.replace(target)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")


if __name__ == "__main__":
    bake()
