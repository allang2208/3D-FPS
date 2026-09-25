"""Author the Fab wooden longbow for the first-person part table."""
from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SRC = HERE / "source.glb"
EXPORT = HERE / "Export"
PREVIEW = HERE / "InspectPreview"
TEX = HERE / "Textures"
EXPORT.mkdir(exist_ok=True)
PREVIEW.mkdir(exist_ok=True)
TEX.mkdir(exist_ok=True)

SCALE = 10.0
DRAW_CM = 28.5
ARROW_Z_CM = 1.5
NAME = "SM_DarkBow_WoodLongbow"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def world_pts(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def bbox_pts(pts):
    xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in pts])
    return {
        "min_m": [min(xs), min(ys), min(zs)],
        "max_m": [max(xs), max(ys), max(zs)],
        "size_m": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
        "center_m": [(min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, (min(zs) + max(zs)) / 2.0],
        "size_cm": [(max(xs) - min(xs)) * 100.0, (max(ys) - min(ys)) * 100.0, (max(zs) - min(zs)) * 100.0],
    }


def cm3(v):
    return [round(v[0] * 100.0, 3), round(v[1] * 100.0, 3), round(v[2] * 100.0, 3)]


def apply_obj(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


reset()
if not SRC.is_file():
    raise SystemExit("missing " + str(SRC))
bpy.ops.import_scene.gltf(filepath=str(SRC))

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh in glb")

string_objs = [o for o in meshes if o.name.startswith("sweep4")]
if not string_objs:
    raise SystemExit("string sweep4 missing")
removed_names = [o.name for o in string_objs]
string_bbox = bbox_pts(sum((world_pts(o) for o in string_objs), []))

wrap_objs = [o for o in meshes if o.name.startswith("sweep") and o not in string_objs]
if not wrap_objs:
    raise SystemExit("grip wrap sweeps missing")
grip = Vector(bbox_pts(sum((world_pts(o) for o in wrap_objs), []))["center_m"])

for obj in string_objs:
    bpy.data.objects.remove(obj, do_unlink=True)

keep = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for obj in keep:
    obj.select_set(True)
bpy.context.view_layer.objects.active = keep[0]
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
for obj in keep:
    apply_obj(obj)

def xform_mesh(target, scale, offset, flip_x):
    for v in target.data.vertices:
        p = v.co * scale + offset
        if flip_x:
            p.x *= -1.0
        v.co = p
    target.data.update()

offset = -grip * SCALE
string_x = (string_bbox["center_m"][0] * SCALE) + offset.x
flipped = string_x > 0.0
for obj in keep:
    xform_mesh(obj, SCALE, offset, flipped)

bpy.ops.object.select_all(action="DESELECT")
for obj in keep:
    obj.select_set(True)
bpy.context.view_layer.objects.active = keep[0]
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = NAME
apply_obj(obj)

pts = world_pts(obj)
box = bbox_pts(pts)
upper = [p for p in pts if p.z > 0.50]
lower = [p for p in pts if p.z < -0.50]
if len(upper) < 8 or len(lower) < 8:
    raise RuntimeError("tip bands empty: %s %s" % (len(upper), len(lower)))

def nock_of(band):
    ordered = sorted(band, key=lambda p: (p.x, abs(p.y)))
    pick = ordered[: max(12, len(ordered) // 40)]
    c = Vector((0.0, 0.0, 0.0))
    for p in pick:
        c += p
    c /= float(len(pick))
    return c

nock_u = nock_of(upper)
nock_l = nock_of(lower)
brace = Vector(((nock_u.x + nock_l.x) * 0.5, (nock_u.y + nock_l.y) * 0.5, ARROW_Z_CM / 100.0))
draw = Vector((brace.x - DRAW_CM / 100.0, brace.y, brace.z))
rest = Vector((0.0, brace.y, brace.z))

for img in bpy.data.images:
    if img.size[0] >= 256:
        dest = TEX / (img.name.replace(".", "_") + ".png")
        img.filepath_raw = str(dest)
        img.file_format = "PNG"
        img.save()

scene = bpy.context.scene
scene.render.resolution_x = 720
scene.render.resolution_y = 1280
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
light = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
light.data.energy = 4.0
scene.collection.objects.link(light)
center = Vector(box["center_m"])
span = max(box["size_m"])

def shoot(name, loc, up=(0.0, 0.0, 1.0)):
    cam.location = loc
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(PREVIEW / name)
    bpy.ops.render.render(write_still=True)

shoot("form_side.png", center + Vector((0.0, span * 1.6, 0.0)))
shoot("form_string.png", center + Vector((span * 1.6, 0.0, 0.0)))
shoot("form_grip.png", Vector((0.12, -0.18, 0.08)))

fbx = EXPORT / (NAME + "_cm.fbx")
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
# UE 5.8 FbxFactory collapses a meter-scale 200k bow to a ~1k stub.
for v in obj.data.vertices:
    v.co *= 100.0
obj.data.update()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "WoodLongbow_Editable.blend"))
bpy.ops.export_scene.fbx(
    filepath=str(fbx),
    use_selection=True,
    object_types={"MESH"},
    axis_forward="-Y",
    axis_up="Z",
    bake_anim=False,
    mesh_smooth_type="OFF",
    use_tspace=False,
    apply_scale_options="FBX_SCALE_ALL",
    path_mode="AUTO",
    embed_textures=False,
    add_leaf_bones=False,
)

receipt = {
    "source": str(SRC),
    "removed": removed_names,
    "scale": SCALE,
    "flipped_x": flipped,
    "tris": sum(len(p.vertices) - 2 for p in obj.data.polygons),
    "verts": len(obj.data.vertices),
    "bbox_cm": {
        "min": cm3(box["min_m"]),
        "max": cm3(box["max_m"]),
        "size": [round(v, 3) for v in box["size_cm"]],
        "origin": cm3(box["center_m"]),
    },
    "nock_upper_cm": cm3(nock_u),
    "nock_lower_cm": cm3(nock_l),
    "brace_nock_cm": cm3(brace),
    "draw_anchor_cm": cm3(draw),
    "arrow_rest_cm": cm3(rest),
    "fbx": str(fbx),
    "textures": [str(p) for p in sorted(TEX.glob("*.png"))],
}
(HERE / "authoring.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("WOOD_LONGBOW_AUTHORED", json.dumps({
    "tris": receipt["tris"],
    "size_cm": receipt["bbox_cm"]["size"],
    "nock_upper_cm": receipt["nock_upper_cm"],
    "nock_lower_cm": receipt["nock_lower_cm"],
    "brace_nock_cm": receipt["brace_nock_cm"],
    "flipped_x": flipped,
}), flush=True)