"""Render current glove pickup meshes to the vertical, transparent backpack icon rules.

Only catalog PNGs and separate icon-authoring scenes are written. Pickup FBX,
UE meshes, first-person materials and animation assets are not re-exported.
"""
import bpy
import ast
import json
import math
import os
import sys
import shutil
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT = Path("D:/FPS3D/FPSGAME")
ICON = ROOT / "Content/ColdSteelData/Icons/ModularOutfit20260924"
SRC = ROOT / "SourceAssets/HandEquipmentAppearance/Source"
AUTHOR = ROOT / "SourceAssets/ModularOutfit20260927/GloveIconDisplayV2"
AUTHOR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/ModularOutfit'))
import glove_icon_display
FILL = 0.91
PX_PER_ROW = 320
SUPERSAMPLE = 2
# Use the same black tint source as the UE material author, without executing
# its Unreal import/save operations inside Blender.
tree = ast.parse((ROOT / 'Tools/ModularOutfit/build_field_glove_leather.py').read_text())
variants = next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'variants' for t in n.targets))
black = variants['M_FieldGloves_Black']
ITEMS = [
    ("ue_field_gloves", ROOT / 'SourceAssets/ModularOutfit20260926/FingerlessHuntV2/Editable/FingerlessHunt_Pickup.blend',
     "SM_FingerlessHunt_Pickup", None, None),
    ("ue_field_gloves_black", ROOT / 'SourceAssets/ModularOutfit20260924/ItemPresentation.blend',
     "SM_FieldGloves_Pickup", black['ColorTint'], black['TintAmount']),
]
if globals().get('ONLY_ITEMS'):
    ITEMS = [row for row in ITEMS if row[0] in ONLY_ITEMS]
# The selected tailored family owns its author mesh and baked PBR. Do not
# restore the earlier smooth shell when a later icon batch includes brown.
outfits = json.loads((ROOT / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
if (outfits['items']['ue_field_gloves'].get('appearance_family') == 'TailoredFingerlessV1'
        and any(row[0] == 'ue_field_gloves' for row in ITEMS)):
    import build_tailored_fingerless_candidate as tailored
    tailored.R = ROOT / 'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    maps = {name: tailored.image(tailored.R / 'Textures' / ('T_TailoredFingerless_'+name+'.png'),
                                'sRGB' if name == 'BaseColor' else 'Non-Color')
            for name in ('BaseColor', 'Roughness', 'Normal')}
    data = json.loads((tailored.R / 'Authored/M4_baked_fullshell.json').read_text())
    tailored.icon(data, tailored.baked_material(maps))
    shutil.copy2(tailored.R / 'TailoredFingerless_Icon.png', ICON / 'ue_field_gloves_fingerless.png')
    ITEMS = [row for row in ITEMS if row[0] != 'ue_field_gloves']
catalog = json.loads((ROOT / 'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
BC = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_BaseColor.jpg"
RG = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Roughness.jpg"
NM = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Normal.jpg"
AO = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_AO.jpg"
CAV = SRC / "Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Cavity.jpg"

assert all(p.is_file() for p in (BC, RG, NM, AO, CAV))
bpy.ops.wm.read_factory_settings(use_empty=True)
ICON.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
subjects = {}
for definition, blend, name, _, _ in ITEMS:
    with bpy.data.libraries.load(str(blend), link=False) as (available, selected):
        selected.objects = [name]
    obj = selected.objects[0]
    assert obj and obj.type == "MESH", name
    scene.collection.objects.link(obj)
    subjects[definition] = obj

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
    width, height = img.size[:]
    pixels = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, img.channels)
    bpy.data.images.remove(img)
    opaque = pixels[:, :, 3] > .95
    encoded = pixels[:, :, :3][opaque]
    linear = np.where(encoded <= .04045, encoded / 12.92, ((encoded + .055) / 1.055) ** 2.4)
    yy, xx = np.where(pixels[:, :, 3] > .05)
    return dict(mean_linear=linear.mean(0).tolist(), mean_srgb=encoded.mean(0).tolist(),
                opaque_pixels=int(opaque.sum()), size=[width, height],
                silhouette_fill=max((xx.max()-xx.min()+1)/width, (yy.max()-yy.min()+1)/height),
                silhouette_center=[float((xx.min()+xx.max()+1)/2/width), float((yy.min()+yy.max()+1)/2/height)])


def scan_color():
    """The brown UE material uses the scan itself, not the retired solid tint."""
    img = bpy.data.images.load(str(BC), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    width, height = img.size[:]
    pixels = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(pixels)
    encoded = pixels.reshape(height, width, img.channels)[::32, ::32, :3]
    mean = np.where(encoded <= .04045, encoded / 12.92, ((encoded + .055) / 1.055) ** 2.4).mean((0, 1))
    bpy.data.images.remove(img)
    return mean.tolist()


report = []
for definition, blend, obj_name, tint, amount in ITEMS:
    source_obj = subjects[definition]
    material = glove_icon_display.black_seams(surface(tint,amount)) if tint is not None else glove_icon_display.brown_seams(source_obj.data.materials[0].copy())
    obj = glove_icon_display.build(definition,material)
    bpy.data.objects.remove(source_obj,do_unlink=True)
    subjects[definition] = obj
    item = catalog[definition]
    canvas_w = max(256, round(PX_PER_ROW * item['grid_w'] / max(1, item['grid_h'])))
    canvas_h = PX_PER_ROW
    aspect = canvas_w / canvas_h
    for other in subjects.values():
        other.hide_render = other is not obj
        other.hide_set(other is not obj)
    # The fingerless source already contains the production scan/metric UV
    # material. Preserve that material rather than coloring the full glove.
    target_color = list(tint) if tint is not None else scan_color()
    x0, x1, y0, y1 = silhouette(obj)
    span_x, span_y = x1 - x0, y1 - y0
    ortho = max(span_x, span_y * aspect) / FILL
    cam_data.ortho_scale = ortho
    cam.location = ((x0 + x1) * 0.5, (y0 + y1) * 0.5, max(span_x, span_y) * 4 + 1)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_x = canvas_w * SUPERSAMPLE
    scene.render.resolution_y = canvas_h * SUPERSAMPLE
    scene.render.resolution_percentage = 100 // SUPERSAMPLE
    target = sum(target_color) / 3.0
    scene.view_settings.exposure = 0.0
    actual, n = 0.0, 0
    out_path = ROOT / 'Content/ColdSteelData' / item['ue_icon']
    for attempt in range(3):
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        got = measure(str(out_path))
        mean, n = got['mean_linear'], got['opaque_pixels']
        actual = sum(mean) / 3.0
        if attempt < 2 and actual > 1e-5:
            delta = math.log2(max(target / actual, 1e-3))
            if abs(delta) < 0.08:
                break
            scene.view_settings.exposure += delta
            continue
        break
    scene_path = AUTHOR / (definition + '_Icon.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
    row = dict(item=definition, material_source_blend=str(blend), source_mesh=obj['SourceMesh'],
               display_contract=obj['Contract'], pose=json.loads(obj['IconPose']),
               world_mesh=item['world_mesh'], world_material=item['world_material'],
               icon=str(out_path), scene=str(scene_path), target_color_linear=target_color,
               exposure=scene.view_settings.exposure, ortho=ortho, **got)
    report.append(row)
    (AUTHOR / (definition + '-icon.json')).write_text(json.dumps(row, indent=2)+'\n')

print("FIELD_GLOVE_ICONS_DONE")
for line in report:
    print(json.dumps(line), flush=True)
