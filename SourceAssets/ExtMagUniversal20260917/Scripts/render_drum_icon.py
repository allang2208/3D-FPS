import bpy, math, os
from mathutils import Matrix, Vector
import numpy as np
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "FBX", "drum", "SM_M4_LargeDrum_new.fbx"))
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][-1]
# neutral FBX frame after import: find the vertical extent along Z (tower axis)
arr = np.array([[v.co.x, v.co.y, v.co.z] for v in ob.data.vertices])
ctr = Vector(arr.mean(axis=0))
h = max(arr[:, 2].max() - arr[:, 2].min(), arr[:, 1].max() - arr[:, 1].min())
ortho = h / 0.82
for nm, base, rough, met in (("DrumPolymer", (0.05, 0.052, 0.056), 0.55, 0.0),
                             ("DrumFasteners", (0.10, 0.10, 0.11), 0.42, 0.85),
                             ("DrumIndex", (0.07, 0.072, 0.078), 0.5, 0.0)):
    m = bpy.data.materials.new(nm); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = met
    while len(ob.data.materials) < 3:
        ob.data.materials.append(None)
    ob.data.materials[["DrumPolymer", "DrumFasteners", "DrumIndex"].index(nm)] = m
scene = bpy.context.scene
scene.render.film_transparent = True
cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = ortho
cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
d = Vector((1, 0, 0))  # camera on -X: muzzle (+Y) appears LEFT, left disc face visible
z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
cam.matrix_world = Matrix.Translation(ctr - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
scene.camera = cam
key = bpy.data.lights.new("key", 'AREA'); key.energy = 55; key.size = 1.2
ko = bpy.data.objects.new("key", key); scene.collection.objects.link(ko)
ko.location = ctr + Vector((-1.3, -0.35, 0.55))
kdir = (ctr - Vector(ko.location)).normalized()
ko.rotation_euler = kdir.to_track_quat('-Z', 'Y').to_euler()
fill = bpy.data.lights.new("fill", 'AREA'); fill.energy = 20; fill.size = 1.5
fo = bpy.data.objects.new("fill", fill); scene.collection.objects.link(fo)
fo.location = ctr + Vector((-0.7, 0.55, -0.5))
fdir = (ctr - Vector(fo.location)).normalized()
fo.rotation_euler = fdir.to_track_quat('-Z', 'Y').to_euler()
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(ROOT, "Reference", "icon_magazine_large_drum.png")
bpy.ops.render.render(write_still=True)
print("DRUM_ICON_DONE")
