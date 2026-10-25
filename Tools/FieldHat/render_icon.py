"""Render the field hat inventory icon and camera-aligned display geometry."""
import json
import math
import shutil
import hashlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path("D:/FPS3D/FPSGAME")
OUT = ROOT / "SourceAssets/FieldHat20261019"
KEY = "ue_field_hat"
FAMILIES = {KEY: "FieldHat20261019"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def measure(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    pixels = np.empty(len(image.pixels), np.float32)
    image.pixels.foreach_get(pixels)
    width, height = image.size
    rgba = pixels.reshape(height, width, 4)
    bpy.data.images.remove(image)
    rgb = rgba[:, :, :3][rgba[:, :, 3] > 0.98]
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    yy, xx = np.where(rgba[:, :, 3] > 0.05)
    return dict(size=[width, height], mean_linear=linear.mean(0).tolist(),
                mean_srgb=(rgb.mean(0) * 255).tolist(),
                fill=max((xx.max() - xx.min() + 1) / width, (yy.max() - yy.min() + 1) / height),
                center=[float((xx.min() + xx.max() + 1) / (2 * width)),
                        float((yy.min() + yy.max() + 1) / (2 * height))])


def export_display(key, obj, camera):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
    mesh.calc_loop_triangles()
    view = camera.matrix_world.inverted()
    normal_matrix = view.to_3x3() @ obj.matrix_world.to_3x3().inverted().transposed()
    points = [view @ (obj.matrix_world @ v.co) for v in mesh.vertices]
    positions = [[-p.z * 100, p.x * 100, p.y * 100] for p in points]
    faces, normals, uv, slots = [], [], [], []
    layer = mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        faces.append(list(tri.vertices))
        slots.append(tri.material_index)
        ns, tex = [], []
        for li in tri.loops:
            n = (normal_matrix @ mesh.corner_normals[li].vector).normalized()
            ns.append([-n.z, n.x, n.y])
            a, b = layer.data[li].uv
            tex.append([a, 1 - b])
        normals.append(ns)
        uv.append(tex)
    path = OUT / (key + "-display.json")
    path.write_text(json.dumps(dict(profile=key, positions=positions, triangles=faces, normals=normals,
                                    uv=uv, triangle_materials=slots,
                                    camera_contract="Final view faces camera -X, screen right +Y, screen up +Z; undo catalog rotation only at UE save"),
                               separators=(",", ":")), encoding="utf-8")
    evaluated.to_mesh_clear()
    return path


def render_current(key, obj, item=None, camera_offset=None):
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    family = ROOT / "SourceAssets" / FAMILIES[key]
    item = item or read(ROOT / "Content/ColdSteelData/items.json")[key]
    for other in list(bpy.context.scene.objects):
        if other.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(other, do_unlink=True)
        elif other.type == "MESH":
            other.hide_render = other != obj
    obj.hide_render = False
    obj.hide_set(False)
    bpy.context.view_layer.update()
    coords = np.array([tuple(obj.matrix_world @ v.co) for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices])
    center = Vector((coords.min(0) + coords.max(0)) * 0.5)
    span = float(np.max(coords.max(0) - coords.min(0)))
    offset = camera_offset or (0.75, 3.0, 0.55)
    camera_data = bpy.data.cameras.new("StandardInventoryCamera")
    camera_data.type = "ORTHO"
    camera_data.clip_start = 0.001
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene = bpy.context.scene
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = center + Vector(offset) * span
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    width = round(320 * item["grid_w"] / item["grid_h"])
    height = 320
    aspect = width / height
    inverse = camera.matrix_world.inverted()
    projected = np.array([tuple(inverse @ Vector(p)) for p in coords])
    low, high = projected.min(0), projected.max(0)
    camera_data.ortho_scale = float(max((high[0] - low[0]) / min(1.0, aspect),
                                        (high[1] - low[1]) * max(1.0, aspect)) / 0.91)
    camera.location += camera.rotation_euler.to_matrix() @ Vector(((low[0] + high[0]) * 0.5,
                                                                  (low[1] + high[1]) * 0.5, 0))
    bpy.context.view_layer.update()
    basis = camera.rotation_euler.to_matrix()
    for name, light_offset, power, size in (("Key", (-0.8, 0.7, 1.5), 35.0, 1.2),
                                            ("Fill", (0.9, 0.1, 1.2), 12.0, 1.5),
                                            ("Rim", (0.2, 1.0, -0.8), 20.0, 0.8)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = power * span * span
        light.size = size * span
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = center + basis @ (Vector(light_offset) * span)
        lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("NeutralInventoryStudio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.35, 0.35, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.12
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 256
    scene.cycles.use_denoising = False
    scene.cycles.adaptive_threshold = 0.004
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    saved = []
    for material in obj.data.materials:
        if not material or not material.use_nodes:
            continue
        nodes, links = material.node_tree.nodes, material.node_tree.links
        bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        orm = next((n for n in nodes if n.type == "TEX_IMAGE" and n.image and "_ORM" in n.image.name), None)
        if orm and not material.get("InventoryAO"):
            split = nodes.new("ShaderNodeSeparateColor")
            links.new(orm.outputs["Color"], split.inputs[0])
            multiply = nodes.new("ShaderNodeMixRGB")
            multiply.blend_type = "MULTIPLY"
            multiply.inputs[0].default_value = 1.0
            if bsdf.inputs["Base Color"].is_linked:
                links.new(bsdf.inputs["Base Color"].links[0].from_socket, multiply.inputs[1])
            else:
                multiply.inputs[1].default_value = bsdf.inputs["Base Color"].default_value
            links.new(split.outputs["Red"], multiply.inputs[2])
            links.new(multiply.outputs[0], bsdf.inputs["Base Color"])
            material["InventoryAO"] = True
        original = out.inputs["Surface"].links[0].from_socket
        emission = nodes.new("ShaderNodeEmission")
        if bsdf.inputs["Base Color"].is_linked:
            links.new(bsdf.inputs["Base Color"].links[0].from_socket, emission.inputs["Color"])
        else:
            emission.inputs["Color"].default_value = bsdf.inputs["Base Color"].default_value
        links.new(emission.outputs[0], out.inputs["Surface"])
        saved.append((material, original, out, emission))
    albedo = OUT / (key + "-albedo.png")
    scene.cycles.samples = 32
    scene.render.filepath = str(albedo)
    bpy.ops.render.render(write_still=True)
    target = measure(albedo)
    for material, original, out, emission in saved:
        material.node_tree.links.new(original, out.inputs["Surface"])
        material.node_tree.nodes.remove(emission)
    scene.cycles.samples = 256
    icon = OUT / (key + ".png")
    scene.render.filepath = str(icon)
    calibration = []
    luma = np.array([0.2126, 0.7152, 0.0722])
    target_luma = float(np.array(target["mean_linear"]) @ luma)
    value = target
    for attempt in range(3):
        bpy.ops.render.render(write_still=True)
        value = measure(icon)
        calibration.append(dict(exposure=scene.view_settings.exposure, **value))
        delta = math.log2(max(target_luma, 1e-7) / max(float(np.array(value["mean_linear"]) @ luma), 1e-7))
        if abs(delta) < 0.035 or attempt == 2:
            break
        scene.view_settings.exposure = float(np.clip(scene.view_settings.exposure + delta, -6, 2))
    display = export_display(key, obj, camera)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (key + "-icon.blend")))
    destinations = [family / (key + ".png"),
                    ROOT / "Content/ColdSteelData" / item["ue_icon"],
                    ROOT / "Content/ColdSteelData/Icons" / (key + ".png")]
    for dest in destinations:
        if dest.resolve() == icon.resolve():
            continue
        backup = OUT / "Before" / ("_".join(dest.relative_to(ROOT).parts))
        backup.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not backup.exists():
            shutil.copy2(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon, dest)
    result = dict(item=key, source=str(OUT / "Authored/hat.json"), size=[width, height],
                  icon=str(icon), display=str(display), target_albedo=target,
                  calibration=calibration, installed=[str(p) for p in destinations],
                  icon_sha256=hashlib.sha256(icon.read_bytes()).hexdigest(), runtime_tested=False)
    save_json(OUT / (key + "-production.json"), result)
    print("FIELD_HAT_ICON_SAVED", value["fill"], value["center"], flush=True)
    return dict(fill=value["fill"], center=value["center"], icon=str(icon), display=str(display),
                calibration=calibration, target=target)


if __name__ == "__main__":
    raise SystemExit("Run from author_boonie.py; this module expects an authored scene.")