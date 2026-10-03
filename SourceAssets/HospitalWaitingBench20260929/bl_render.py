# Visual sanity render of the ORIGINAL glTF (author intent) for the hospital bed.
import bpy
import math
from mathutils import Vector

SRC = "D:/FPS3D/FPSGAME/SourceAssets/HospitalWaitingBench20260929/Hospital_Waiting_Bench.glb"
OUT = "D:/FPS3D/FPSGAME/SourceAssets/HospitalWaitingBench20260929/verify/bench_source_render.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
center = (lo + hi) * 0.5
size = (hi - lo).length

# camera 3/4 view
cam_data = bpy.data.cameras.new("cam")
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
dist = size * 1.4
cam.location = center + Vector((dist * 0.6, -dist * 0.75, dist * 0.35))
bpy.context.scene.camera = cam

# aim camera at center
direction = center - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

# lights
sun_data = bpy.data.lights.new("sun", "SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("sun", sun_data)
bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))

# ground for shadow reference
bpy.ops.mesh.primitive_plane_add(size=size * 10,
                                 location=(center.x, center.y, lo.z - 0.01))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("BLENDER_RENDER_DONE", OUT)
