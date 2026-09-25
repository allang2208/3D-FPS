"""Re-render the brown hunt-glove icon from a 3/4 dorsal view."""
import math
from pathlib import Path
import bpy
from mathutils import Euler, Vector

ROOT = Path("D:/FPS3D/FPSGAME")
BLEND = ROOT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1/HuntItemPresentation.blend"
ICON = ROOT / "Content/ColdSteelData/Icons/ModularOutfit20260924/ue_field_gloves.png"
FILL = 0.91
PX = 320
SUPERSAMPLE = 2

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
obj = bpy.data.objects.get("SM_HuntFieldGloves_Pickup")
assert obj and obj.type == "MESH"
scene = bpy.context.scene
cam = scene.camera
xs = [v.co.x for v in obj.data.vertices]
ys = [v.co.y for v in obj.data.vertices]
zs = [v.co.z for v in obj.data.vertices]
cx, cy, cz = (min(xs)+max(xs))*0.5, (min(ys)+max(ys))*0.5, (min(zs)+max(zs))*0.5
span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
# Tilt so knuckle pads and cuff roll read in the catalog, not a flat exam-glove top view.
cam.location = (cx + span*0.18, cy - span*0.55, cz + span*0.85)
cam.rotation_euler = Euler((math.radians(48), 0.0, math.radians(18)), "XYZ")
if cam.data:
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = span / FILL
    cam.data.clip_start = 0.01
scene.render.resolution_x = PX * SUPERSAMPLE
scene.render.resolution_y = PX * SUPERSAMPLE
scene.render.resolution_percentage = 100 // SUPERSAMPLE
scene.render.filepath = str(ICON)
scene.render.film_transparent = True
scene.view_settings.exposure = 0.0
target = 0.069

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
    bpy.ops.render.render(write_still=True)
    got = measure(str(ICON))
    if not got:
        break
    mean, count = got
    actual = sum(mean) / 3.0
    if attempt < 2 and actual > 1e-5:
        delta = math.log2(max(target / actual, 1e-3))
        if abs(delta) < 0.08:
            break
        scene.view_settings.exposure += delta
print("HUNT_ICON_TILT", f"rendered={actual:.4f}", f"px={count}", flush=True)
