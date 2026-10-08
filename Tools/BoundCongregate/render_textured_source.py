"""Render the authored mesh and its real source maps; does not launch UE or gameplay."""
from pathlib import Path
import bpy
from mathutils import Vector

root = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
out = root / 'Preview20261007'
out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root / 'Authoring/BoundCongregate_Clothed_Rig.blend'))
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type in {'CAMERA', 'LIGHT'}:
        bpy.data.objects.remove(ob, do_unlink=True)
scene.frame_set(1)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = 0
scene.world = bpy.data.worlds.new('BC_MaterialPreview')
scene.world.use_nodes = True
nodes = scene.world.node_tree.nodes
nodes.clear()
background = nodes.new('ShaderNodeBackground')
output = nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs[0], output.inputs['Surface'])
background.inputs[0].default_value = (.19, .21, .23, 1)
background.inputs[1].default_value = .3
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.02))
floor = bpy.context.object
floor.name = 'PreviewFloor'
mat = bpy.data.materials.new('PreviewFloor'); mat.use_nodes = True
shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
shader.inputs['Base Color'].default_value = (.07, .08, .09, 1)
shader.inputs['Roughness'].default_value = .9
floor.data.materials.append(mat)
target = Vector((0, 0, 1.1))
for name, location, power, size in [('Key', (-3,-4,6), 1100, 4), ('Fill',(4,-2,3), 500, 3), ('Rim',(1,4,5), 900, 3)]:
    light = bpy.data.lights.new(name, 'AREA'); light.energy = power; light.shape = 'DISK'; light.size = size
    ob = bpy.data.objects.new(name, light); scene.collection.objects.link(ob); ob.location = location
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z','Y').to_euler()
data = bpy.data.cameras.new('PreviewCamera')
cam = bpy.data.objects.new('PreviewCamera', data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (4.9, -7.7, 3.6)
cam.rotation_euler = (target - cam.location).to_track_quat('-Z','Y').to_euler()
data.type = 'ORTHO'; data.ortho_scale = 5.45
scene.render.filepath = str(out / 'BoundCongregate_Textured_Source.png')
bpy.ops.render.render(write_still=True)
