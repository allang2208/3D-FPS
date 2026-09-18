"""Render the AKM factory magazine from several sides to locate the bottom defect."""
import bpy
import math
import os
import sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "Reference")
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = ARGV[0] if ARGV else (r"D:\FPS3D\FPSGAME\SourceAssets\PhantomRearGripIntegration20260913"
                            r"\AKM\SK_AKM_MannyNative.fbx")
LABEL = ARGV[1] if len(ARGV) > 1 else "akm_factory_mag"
OBJECT = ARGV[2] if len(ARGV) > 2 else "AKM_FactoryMagazine_Preview"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
if OBJECT == "MESH":
    ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
elif OBJECT in bpy.data.objects:
    ob = bpy.data.objects[OBJECT]
else:
    ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
for other in list(bpy.context.scene.objects):
    if other is not ob:
        bpy.data.objects.remove(other, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

points = [ob.matrix_world @ v.co for v in ob.data.vertices]
lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
center = (lo + hi) * 0.5
size = (hi - lo).length

for name, offset in (("front", Vector((0, -1, 0))), ("back", Vector((0, 1, 0))),
                     ("left", Vector((-1, 0, 0))), ("bottom", Vector((0, -0.35, -1))),
                     ("threequarter", Vector((-0.8, -0.6, -0.5)))):
    direction = offset.normalized()
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = size * 0.85
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.matrix_world = (Matrix.Translation(center - direction * size)
                        @ (-direction).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    scene.camera = cam
    key = bpy.data.lights.new("k" + name, 'AREA')
    key.energy = 80
    key.size = 1.0
    ko = bpy.data.objects.new("k" + name, key)
    scene.collection.objects.link(ko)
    ko.location = center - direction * 0.6 + Vector((0.3, -0.3, 0.3))
    ko.rotation_euler = (math.radians(55), 0, math.radians(40))
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (LABEL, name))
    bpy.ops.render.render(write_still=True)
    print("AKM_MAG_VIEW", name, flush=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(ko, do_unlink=True)
print("AKM_MAG_VIEWS_DONE", flush=True)
