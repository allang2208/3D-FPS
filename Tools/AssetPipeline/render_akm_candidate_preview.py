import bpy
from pathlib import Path
from mathutils import Vector

SOURCE = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend")
OUTPUT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM\akm_reload_empty_candidate.png")

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUTPUT)
scene.render.film_transparent = False
scene.world.color = (0.012, 0.016, 0.025)

rig = bpy.data.objects["SK_AKM_Viewmodel"]
action = bpy.data.actions["AKM_reload_empty"]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(52)
bpy.context.view_layer.update()

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.parent == rig and not obj.hide_render]
points = []
depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in meshes:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
    evaluated.to_mesh_clear()
minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
center = (minimum + maximum) * 0.5

camera_data = bpy.data.cameras.new("CandidateCamera")
camera = bpy.data.objects.new("CandidateCamera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = center + Vector((1.05, -1.35, 0.55))
camera.rotation_euler = ((center - camera.location).to_track_quat("-Z", "Y")).to_euler()
camera_data.lens = 62
scene.camera = camera

for name, offset, energy, size, color in (
    ("Key", Vector((1.2, -0.8, 1.4)), 900.0, 3.0, (1.0, 0.88, 0.72)),
    ("Fill", Vector((-1.0, -0.3, 0.5)), 650.0, 2.5, (0.48, 0.68, 1.0)),
    ("Rim", Vector((0.2, 1.0, 1.0)), 1000.0, 2.0, (0.75, 0.86, 1.0)),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_data.color = color
    light = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light)
    light.location = center + offset
    light.rotation_euler = ((center - light.location).to_track_quat("-Z", "Y")).to_euler()

scene.view_settings.look = "AgX - Medium High Contrast"
bpy.ops.render.render(write_still=True)
print(f"AKM_CANDIDATE_PREVIEW={OUTPUT}")
