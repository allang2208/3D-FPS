import bpy
import math
import os
from mathutils import Vector

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mat = bpy.data.materials.new("Clay")
mat.use_nodes = True
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.33, 1)
bsdf.inputs["Roughness"].default_value = 0.65
for i in range(len(obj.data.materials)):
    obj.data.materials[i] = mat
for o in list(bpy.context.scene.objects):
    if o.type not in {"MESH", "CAMERA", "LIGHT"}:
        bpy.data.objects.remove(o, do_unlink=True)
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("W")
bpy.context.scene.world.use_nodes = True
bg = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.02, 0.022, 0.025, 1)
bg.inputs["Strength"].default_value = 0.5

# left-side buckle centre from component inspection
centre = Vector((-0.2361, -0.080, -0.0336))
bpy.ops.object.empty_add(type="PLAIN_AXES", location=centre)
target = bpy.context.object

bpy.ops.object.camera_add(location=(centre.x - 0.12, centre.y - 0.015, centre.z + 0.01))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.052
con = cam.constraints.new(type="TRACK_TO")
con.target = target; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
bpy.context.scene.camera = cam

for name, loc, energy, size in (
    ("Key", (centre.x - 0.08, centre.y - 0.08, centre.z + 0.09), 8.0, 0.08),
    ("Fill", (centre.x - 0.06, centre.y + 0.06, centre.z + 0.02), 3.0, 0.10),
):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object; l.data.energy = energy; l.data.size = size
    c = l.constraints.new(type="TRACK_TO"); c.target = target; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.look = "None"
scene.render.filepath = os.path.join(ROOT, "Preview", "buckle_left_side.png")
bpy.ops.render.render(write_still=True)

# 3/4 from outside/front
cam.location = (centre.x - 0.10, centre.y - 0.065, centre.z + 0.045)
cam.data.ortho_scale = 0.060
scene.render.filepath = os.path.join(ROOT, "Preview", "buckle_left_3q.png")
bpy.ops.render.render(write_still=True)

# Front release buckle opening (left of centre).
front = Vector((-0.0617, -0.1392, 0.1329))
target.location = front
cam.constraints.remove(con)
cam.location = (front.x - 0.045, front.y - 0.20, front.z + 0.045)
cam.data.ortho_scale = 0.070
con = cam.constraints.new(type="TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.render.filepath = os.path.join(ROOT, "Preview", "buckle_front_open.png")
bpy.ops.render.render(write_still=True)
print("BUCKLE_RENDER done")