import bpy, math, os
from mathutils import Matrix, Vector
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "FBX", "SM_ExtMag_Universal.fbx"))
mag = [o for o in bpy.context.scene.objects if o.type == "MESH"][-1]
# actual game-look materials: dark polymer body, dark metal baseplate
for slot_idx, base in ((0, (0.045, 0.046, 0.052)), (1, (0.09, 0.09, 0.10))):
    m = bpy.data.materials.new(f"icon_mat_{slot_idx}"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = 0.5
    b.inputs["Metallic"].default_value = 0.85 if slot_idx == 1 else 0.0
    if slot_idx < len(mag.data.materials):
        mag.data.materials[slot_idx] = m
    else:
        mag.data.materials.append(m)
scene = bpy.context.scene
scene.render.film_transparent = True
dims = mag.dimensions
h = max(dims.y, dims.z)
ortho = h / 0.80
cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
cam = bpy.data.objects.new("c", cam_d); scene.collection.objects.link(cam)
center = Vector((0, 0.0235, -0.105))
d = Vector((1, 0, 0))  # camera on -X looking +X: +Y (mag front) appears LEFT
z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
cam.matrix_world = Matrix.Translation(center - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
scene.camera = cam
key = bpy.data.lights.new("key", 'AREA'); key.energy = 60; key.size = 1.2
ko = bpy.data.objects.new("key", key); scene.collection.objects.link(ko)
ko.location = (-0.6, -0.5, 0.5); ko.rotation_euler = (math.radians(55), 0, math.radians(50))
fill = bpy.data.lights.new("fill", 'AREA'); fill.energy = 25; fill.size = 1.5
fo = bpy.data.objects.new("fill", fill); scene.collection.objects.link(fo)
fo.location = (0.5, 0.6, -0.2); fo.rotation_euler = (math.radians(100), 0, math.radians(-130))
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(ROOT, "Reference", "icon_magazine_ext_mag.png")
bpy.ops.render.render(write_still=True)
print("ICON_RENDER_DONE")
