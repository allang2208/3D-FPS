"""Flatten the authored M4 hunt gloves for the brown pickup and catalog icon."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT = Path("D:/FPS3D/FPSGAME")
ROOT = PROJECT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1"
SOURCES = PROJECT / "SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources"
EXPORT = PROJECT / "SourceAssets/ModularOutfit20260924/Exports"
ICON = PROJECT / "Content/ColdSteelData/Icons/ModularOutfit20260924"
SRC = PROJECT / "SourceAssets/HandEquipmentAppearance/Source"
AUTH = ROOT / "Authored/M4.json"
FILL = 0.91
PX = 320
SUPERSAMPLE = 2
BC = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_BaseColor.jpg"
RG = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Roughness.jpg"
NM = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Normal.jpg"
AO = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_AO.jpg"
CAV = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Cavity.jpg"

data = json.loads(AUTH.read_text(encoding="utf-8-sig"))
bones = json.loads((SOURCES / "M4.json").read_text(encoding="utf-8-sig"))["bones"]
EXPORT.mkdir(parents=True, exist_ok=True)
ICON.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new("SM_HuntFieldGloves_Pickup")
mesh.from_pydata([(p[0] * 0.01, -p[1] * 0.01, p[2] * 0.01) for p in data["positions"]], [], data["triangles"])
mesh.update()
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(obj)

frames = {}
for side in ("l", "r"):
    h = Vector((bones["hand_" + side]["position"][0] * 0.01,
                -bones["hand_" + side]["position"][1] * 0.01,
                bones["hand_" + side]["position"][2] * 0.01))
    tip = Vector((bones["middle_03_" + side]["position"][0] * 0.01,
                  -bones["middle_03_" + side]["position"][1] * 0.01,
                  bones["middle_03_" + side]["position"][2] * 0.01))
    idx = Vector((bones["index_01_" + side]["position"][0] * 0.01,
                  -bones["index_01_" + side]["position"][1] * 0.01,
                  bones["index_01_" + side]["position"][2] * 0.01))
    pnk = Vector((bones["pinky_01_" + side]["position"][0] * 0.01,
                  -bones["pinky_01_" + side]["position"][1] * 0.01,
                  bones["pinky_01_" + side]["position"][2] * 0.01))
    forward = (tip - h).normalized()
    across = (idx - pnk).normalized()
    normal = across.cross(forward).normalized()
    across = forward.cross(normal).normalized()
    frames[side] = (h, forward, across, normal)

for v in obj.data.vertices:
    side = "l" if v.co.x < 0 else "r"
    h, f, a, n = frames[side]
    p = v.co - h
    v.co = Vector((p.dot(a) + (-0.062 if side == "l" else 0.062), p.dot(f) - 0.04, p.dot(n)))

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
fbx = EXPORT / "SM_HuntFieldGloves_Pickup.fbx"
bpy.ops.export_scene.fbx(
    filepath=str(fbx), use_selection=True, object_types={"MESH"},
    axis_forward="-Y", axis_up="Z", bake_anim=False, mesh_smooth_type="FACE", path_mode="STRIP")


def image(path, color=False):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return img


m = bpy.data.materials.new("HuntIconLeather")
m.use_nodes = True
t = m.node_tree
t.nodes.clear()
p = t.nodes.new("ShaderNodeBsdfPrincipled")
o = t.nodes.new("ShaderNodeOutputMaterial")
texc = t.nodes.new("ShaderNodeTexCoord")
mapn = t.nodes.new("ShaderNodeMapping")
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
nmap.inputs["Strength"].default_value = 0.72
shade = t.nodes.new("ShaderNodeMix")
shade.data_type = "RGBA"
shade.blend_type = "MULTIPLY"
shade.inputs["Factor"].default_value = 0.30
cavity = t.nodes.new("ShaderNodeMix")
cavity.data_type = "RGBA"
cavity.blend_type = "MULTIPLY"
cavity.inputs["Factor"].default_value = 0.18
contrast = t.nodes.new("ShaderNodeBrightContrast")
contrast.inputs["Contrast"].default_value = 0.18
t.links.new(texc.outputs["Object"], mapn.inputs["Vector"])
for node in (col, rough, nrm, ao, cav):
    t.links.new(mapn.outputs["Vector"], node.inputs["Vector"])
t.links.new(col.outputs["Color"], shade.inputs["A"])
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
obj.data.materials.clear()
obj.data.materials.append(m)

scene = bpy.context.scene
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
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.shape, light.size = power, "DISK", size
    lamp = bpy.data.objects.new(name, light)
    scene.collection.objects.link(lamp)
    lamp.location = pos
    lamp.rotation_euler = (-Vector(pos)).to_track_quat("-Z", "Y").to_euler()
if not scene.world:
    scene.world = bpy.data.worlds.new("SoftStudio")
scene.world.use_nodes = True
tree = scene.world.node_tree
tree.nodes.clear()
bg = tree.nodes.new("ShaderNodeBackground")
outw = tree.nodes.new("ShaderNodeOutputWorld")
tree.links.new(bg.outputs[0], outw.inputs["Surface"])
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
xs = [v.co.x for v in obj.data.vertices]
ys = [v.co.y for v in obj.data.vertices]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
span_x, span_y = x1 - x0, y1 - y0
cam_data.ortho_scale = max(span_x, span_y) / FILL
cam.location = ((x0 + x1) * 0.5, (y0 + y1) * 0.5, max(span_x, span_y) * 4 + 1)
cam.rotation_euler = (0.0, 0.0, 0.0)
scene.render.resolution_x = PX * SUPERSAMPLE
scene.render.resolution_y = PX * SUPERSAMPLE
scene.render.resolution_percentage = 100 // SUPERSAMPLE
out_path = ICON / "ue_field_gloves.png"
target = 0.069
scene.view_settings.exposure = 0.0


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


actual = 0.0
count = 0
for attempt in range(3):
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    got = measure(str(out_path))
    if not got:
        break
    mean, count = got
    actual = sum(mean) / 3.0
    if attempt < 2 and actual > 1e-5:
        delta = math.log2(max(target / actual, 1e-3))
        if abs(delta) < 0.08:
            break
        scene.view_settings.exposure += delta
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "HuntItemPresentation.blend"))
print("HUNT_PRESENTATION_SAVED", fbx, out_path, f"rendered={actual:.4f}", f"px={count}", flush=True)
