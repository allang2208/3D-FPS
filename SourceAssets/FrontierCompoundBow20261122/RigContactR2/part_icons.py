"""Render original factory components with the project's saved ImageGen steel frame."""
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

source = Path(__file__).resolve().parent
project = Path(sys.argv[sys.argv.index('--') + 1])
frame_path = project / 'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png'
bpy.ops.wm.open_mainfile(filepath=str(source / 'FrontierCompoundBow_R2.blend'))
scene = bpy.context.scene
scene.frame_set(1)
camera = bpy.data.cameras.new('PartCamera')
camera.type = 'ORTHO'
camera.clip_end = 700
cam = bpy.data.objects.new('PartCamera', camera)
scene.collection.objects.link(cam)
scene.camera = cam
scene.world = bpy.data.worlds.new('Studio')
scene.world.use_nodes = True
background = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs[0].default_value = (.74, .74, .74, 1)
surface = bpy.data.materials['M_Frontier_Surface']
nodes = surface.node_tree.nodes
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
base = bsdf.inputs['Base Color']
if base.is_linked:
    color = base.links[0].from_socket
    gray = nodes.new('ShaderNodeRGBToBW')
    surface.node_tree.links.new(color, gray.inputs[0])
    surface.node_tree.links.new(gray.outputs[0], base)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.color_mode = 'RGBA'
direction = Vector((.2, -1, .12)).normalized()
lights = []
for offset, energy in [((40,-70,75),150000),((-35,30,60),95000)]:
    lamp = bpy.data.lights.new('Softbox', 'AREA')
    lamp.energy = energy
    lamp.size = 60
    obj = bpy.data.objects.new('Softbox',lamp)
    scene.collection.objects.link(obj)
    lights.append((obj,Vector(offset)))
mesh_objects = [o for o in scene.objects if o.type == 'MESH']
# The saved frame is the project-approved empty version of the ImageGen master.
frame = bpy.data.images.load(str(frame_path), check_existing=False)
frame.scale(512,512)
import numpy as np
def pixels(image):
    buffer = np.empty(512*512*4,dtype=np.float32)
    image.pixels.foreach_get(buffer)
    return buffer.reshape(512,512,4)
plate = pixels(frame)
luma = np.array([.2126,.7152,.0722],dtype=np.float32)
plate[:,:,:3] = (plate[:,:,:3] @ luma)[:,:,None]
icon_dir = source/'Export/PartIcons'
icon_dir.mkdir(exist_ok=True)
for slot, names in {'riser':('Riser','UpperLimb','LowerLimb','UpperCam','LowerCam'),
                    'arrow_rest':('Rest',)}.items():
    for ob in mesh_objects:
        ob.hide_render = ob.name not in names
    selected = [scene.objects[name] for name in names]
    cam.rotation_euler = (-direction).to_track_quat('-Z','Y').to_euler()
    if slot == 'riser':
        cam.rotation_euler.rotate_axis('Z', math.radians(22))
    rot = cam.rotation_euler.to_matrix()
    points = [rot.inverted() @ (ob.matrix_world @ v.co) for ob in selected for v in ob.data.vertices]
    lo = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    center = rot @ ((lo+hi)/2)
    cam.location = center+direction*155
    camera.ortho_scale = max(hi.x-lo.x,hi.y-lo.y)/.68
    for ob, off in lights:
        ob.location = center+off
        ob.rotation_euler = (-off).to_track_quat('-Z','Y').to_euler()
    raw = icon_dir/(slot+'_subject.png')
    scene.render.filepath = str(raw)
    bpy.ops.render.render(write_still=True)
    rendered = bpy.data.images.load(str(raw),check_existing=False)
    fore = pixels(rendered)
    alpha = fore[:,:,3:4]
    result = plate.copy()
    result[:,:,:3] = (fore[:,:,:3] @ luma)[:,:,None]*alpha + plate[:,:,:3]*(1-alpha)
    result[:,:,3:4] = alpha + plate[:,:,3:4]*(1-alpha)
    out = bpy.data.images.new(slot,512,512,alpha=True)
    out.pixels.foreach_set(result.ravel())
    out.filepath_raw = str(icon_dir/('bow_frontier_compound_'+slot+'_false.png'))
    out.file_format = 'PNG'
    out.save()
