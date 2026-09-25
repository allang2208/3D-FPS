"""Re-render the two field-glove catalog icons with the licensed leather scan."""
import bpy
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT = Path("D:/FPS3D/FPSGAME")
BLEND = ROOT / "SourceAssets/ModularOutfit20260924/ItemPresentation.blend"
ICON = ROOT / "Content/ColdSteelData/Icons/ModularOutfit20260924"
SRC = ROOT / "SourceAssets/HandEquipmentAppearance/Source"
FILL = 0.91
PX_PER_ROW = 320
SUPERSAMPLE = 2
ITEMS = [
    ("ue_field_gloves", "SM_FieldGloves_Pickup", (1.0, 1.0, 1.0), 0.0),
    ("ue_field_gloves_black", "SM_FieldGloves_Pickup", (0.016, 0.018, 0.022), 1.0),
]
BC = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_BaseColor.jpg"
RG = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Roughness.jpg"
NM = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Normal.jpg"
AO = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_AO.jpg"
CAV = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Cavity.jpg"

assert BLEND.exists(), BLEND
assert all(p.is_file() for p in (BC, RG, NM, AO, CAV))
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
ICON.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
subjects = {}
for _, name, _, _ in ITEMS:
    obj = bpy.data.objects.get(name)
    assert obj and obj.type == "MESH", name
    subjects[name] = obj

for o in list(bpy.data.objects):
    if o.type == "CAMERA":
        bpy.data.objects.remove(o, do_unlink=True)
cam_data = bpy.data.cameras.new("IconCamera")
cam_data.type = "ORTHO"
cam_data.clip_start = 0.01
cam = bpy.data.objects.new("IconCamera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
for o in list(bpy.data.objects):
    if o.type == "LIGHT":
        bpy.data.objects.remove(o, do_unlink=True)
for name, pos, power, size in [("Key", (-0.7, -0.8, 1.6), 90, 0.55), ("Fill", (1.1, 0.3, 1.2), 22, 1.2), ("Rim", (0.1, 1.0, 0.9), 40, 0.7)]:
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size = power, "DISK", size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (-Vector(pos)).to_track_quat("-Z", "Y").to_euler()
if not scene.world:
    scene.world = bpy.data.worlds.new("SoftStudio")
scene.world.use_nodes = True
tree = scene.world.node_tree
tree.nodes.clear()
bg = tree.nodes.new("ShaderNodeBackground")
out = tree.nodes.new("ShaderNodeOutputWorld")
tree.links.new(bg.outputs[0], out.inputs["Surface"])
bg.inputs["Color"].default_value = (0.25, 0.28, 0.34, 1)
bg.inputs["Strength"].default_value = 0.12
scene.view_settings.view_transform = "Standard"
try:
    scene.view_settings.look = "None"
except Exception:
    pass
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
try:
    scene.cycles.device = "CPU"
except Exception:
    pass
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"


def image(path, color=False):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return img


def surface(tint, amount):
    m = bpy.data.materials.new("IconLeather")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    p = t.nodes.new("ShaderNodeBsdfPrincipled")
    o = t.nodes.new("ShaderNodeOutputMaterial")
    texc = t.nodes.new("ShaderNodeTexCoord")
    mapn = t.nodes.new("ShaderNodeMapping")
    # Pickup is ~26 cm. In-game 25 cm tiles collapse to 1–3 px at 320; 8 cm keeps grain readable.
    mapn.inputs["Scale"].default_value = (12.5, 12.5, 12.5)
    col = t.nodes.new("ShaderNodeTexImage")
    col.image = image(BC, True)
    rough = t.nodes.new("ShaderNodeTexImage")
    rough.image = image(RG, False)
    nrm = t.nodes.new("ShaderNodeTexImage")
    nrm.image = image(NM, False)
    ao = t.nodes.new("ShaderNodeTexImage")
    ao.image = image(AO, False)
    cav = t.nodes.new("ShaderNodeTexImage")
    cav.image = image(CAV, False)
    sep = t.nodes.new("ShaderNodeSeparateColor")
    comb = t.nodes.new("ShaderNodeCombineColor")
    flip = t.nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1.0
    nmap = t.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.72 if amount < 0.5 else 0.62
    mid = t.nodes.new("ShaderNodeVectorMath")
    mid.operation = "DIVIDE"
    mid.inputs[1].default_value = (0.069, 0.069, 0.069) if amount < 0.5 else (0.10, 0.10, 0.10)
    tint_mul = t.nodes.new("ShaderNodeVectorMath")
    tint_mul.operation = "MULTIPLY"
    tint_mul.inputs[1].default_value = tint
    mix = t.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    mix.inputs["Factor"].default_value = amount
    shade = t.nodes.new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs["Factor"].default_value = 0.30 if amount < 0.5 else 0.16
    cavity = t.nodes.new("ShaderNodeMix")
    cavity.data_type = "RGBA"
    cavity.blend_type = "MULTIPLY"
    cavity.inputs["Factor"].default_value = 0.18 if amount < 0.5 else 0.10
    contrast = t.nodes.new("ShaderNodeBrightContrast")
    contrast.inputs["Contrast"].default_value = 0.18
    t.links.new(texc.outputs["Object"], mapn.inputs["Vector"])
    for node in (col, rough, nrm, ao, cav):
        t.links.new(mapn.outputs["Vector"], node.inputs["Vector"])
    t.links.new(col.outputs["Color"], mid.inputs[0])
    t.links.new(mid.outputs["Vector"], tint_mul.inputs[0])
    t.links.new(col.outputs["Color"], mix.inputs["A"])
    t.links.new(tint_mul.outputs["Vector"], mix.inputs["B"])
    t.links.new(mix.outputs["Result"], shade.inputs["A"])
    t.links.new(ao.outputs["Color"], shade.inputs["B"])
    t.links.new(shade.outputs["Result"], cavity.inputs["A"])
    t.links.new(cav.outputs["Color"], cavity.inputs["B"])
    t.links.new(cavity.outputs["Result"], contrast.inputs["Color"])
    t.links.new(contrast.outputs["Color"], p.inputs["Base Color"])
    t.links.new(rough.outputs["Color"], p.inputs["Roughness"])
    t.links.new(nrm.outputs["Color"], sep.inputs["Color"])
    t.links.new(sep.outputs["Red"], comb.inputs["Red"])
    t.links.new(sep.outputs["Green"], flip.inputs[1])
    t.links.new(flip.outputs["Value"], comb.inputs["Green"])
    t.links.new(sep.outputs["Blue"], comb.inputs["Blue"])
    t.links.new(comb.outputs["Color"], nmap.inputs["Color"])
    t.links.new(nmap.outputs["Normal"], p.inputs["Normal"])
    t.links.new(p.outputs["BSDF"], o.inputs["Surface"])
    p.inputs["Specular IOR Level"].default_value = 0.35
    p.inputs["Metallic"].default_value = 0.0
    return m


def silhouette(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    return min(xs), max(xs), min(ys), max(ys)


def measure(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    px = list(img.pixels)
    ch = img.channels
    acc = [0.0, 0.0, 0.0]
    n = 0
    for i in range(0, len(px), ch * 7):
        if px[i + 3] > 0.15:
            acc[0] += px[i]
            acc[1] += px[i + 1]
            acc[2] += px[i + 2]
            n += 1
    bpy.data.images.remove(img)
    if not n:
        return None

    def to_linear(e):
        return e / 12.92 if e <= 0.04045 else ((e + 0.055) / 1.055) ** 2.4

    return [to_linear(acc[k] / n) for k in range(3)], n


report = []
for definition, obj_name, tint, amount in ITEMS:
    obj = subjects[obj_name]
    canvas_w = canvas_h = PX_PER_ROW
    aspect = 1.0
    for other in subjects.values():
        other.hide_render = other is not obj
    obj.data.materials.clear()
    obj.data.materials.append(surface(tint, amount))
    x0, x1, y0, y1 = silhouette(obj)
    span_x, span_y = x1 - x0, y1 - y0
    ortho = max(span_x, span_y * aspect) / FILL
    cam_data.ortho_scale = ortho
    cam.location = ((x0 + x1) * 0.5, (y0 + y1) * 0.5, max(span_x, span_y) * 4 + 1)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_x = canvas_w * SUPERSAMPLE
    scene.render.resolution_y = canvas_h * SUPERSAMPLE
    scene.render.resolution_percentage = 100 // SUPERSAMPLE
    target = 0.069 if amount < 0.5 else 0.022
    scene.view_settings.exposure = 0.0
    actual, n = 0.0, 0
    out_path = ICON / (definition + ".png")
    for attempt in range(3):
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        got = measure(str(out_path))
        if not got:
            report.append(definition + ": empty")
            break
        mean, n = got
        actual = sum(mean) / 3.0
        if attempt < 2 and actual > 1e-5:
            delta = math.log2(max(target / actual, 1e-3))
            if abs(delta) < 0.08:
                break
            scene.view_settings.exposure += delta
            continue
        break
    report.append(
        f"{definition}: canvas={canvas_w}x{canvas_h} ortho={ortho:.4f} "
        f"target={target:.4f} rendered={actual:.4f} exposure={scene.view_settings.exposure:+.2f}EV px={n}"
    )

print("FIELD_GLOVE_ICONS_DONE")
for line in report:
    print("  " + line)
