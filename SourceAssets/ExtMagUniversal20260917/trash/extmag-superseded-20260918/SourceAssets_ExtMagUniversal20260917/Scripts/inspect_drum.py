import bpy, math, os, json
from mathutils import Matrix, Vector
import numpy as np
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
DRUMS = {
    "M4": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\M4\drum.fbx"),
    "AKM": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\AKM\drum.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191Attachments20260913\SM_QBZ191_drum.fbx"),
}
report = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
# render M4 drum isolated, 3/4 view
bpy.ops.import_scene.fbx(filepath=DRUMS["M4"])
mo = [o for o in bpy.context.scene.objects if o.type == "MESH"][-1]
print("M4 drum slots:", [m.name if m else None for m in mo.data.materials])
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and o is not mo:
        o.hide_render = True
scene = bpy.context.scene
cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 0.3
cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
d = Vector((1, -0.8, 0.35)).normalized()
z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
ctr = Vector((0.065, 0.265, -0.14))
cam.matrix_world = Matrix.Translation(ctr - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
scene.camera = cam
sun = bpy.data.lights.new("s", 'SUN'); sun.energy = 3.5
so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so); so.rotation_euler = (math.radians(55), 0, math.radians(35))
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
scene.world = w; scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.filepath = os.path.join(ROOT, "Reference", "drum_current_iso.png")
bpy.ops.render.render(write_still=True)
print("CURRENT_DRUM_RENDER_DONE")
