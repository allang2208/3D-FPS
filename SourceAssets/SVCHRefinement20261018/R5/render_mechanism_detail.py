"""Uniform clay close-ups of authored R4/R5 geometry; no saved UE asset edits."""
import bpy
import json
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector

O = Path(__file__).resolve().parent
version = sys.argv[sys.argv.index('--') + 1]
source = O / 'SVCH_Refined_R5.blend' if version == 'R5' else O.parent / 'SVCH_Refined.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
hold = json.loads((O.parent.parent / 'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text())
R, T = np.array(hold['R']), np.array(hold['t_cm'])

def point(p):
    q = np.array((p[0] - 18.7444, p[2] - 1.5268, p[1])) @ R.T + T
    return Vector((q[0] / 100, -q[1] / 100, q[2] / 100))

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 800
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new('DetailWorld')
scene.world.use_nodes = True
world_nodes = scene.world.node_tree.nodes
world_nodes.clear()
background = world_nodes.new('ShaderNodeBackground')
world_output = world_nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs['Background'], world_output.inputs['Surface'])
background.inputs['Color'].default_value = (.14, .17, .22, 1)
background.inputs['Strength'].default_value = .5
clay = bpy.data.materials.new('R5_Review_Clay')
clay.use_nodes = True
bsdf = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value = (.32, .36, .40, 1)
bsdf.inputs['Roughness'].default_value = .32
bsdf.inputs['Metallic'].default_value = .45
for ob in scene.objects:
    if ob.type == 'MESH':
        ob.hide_render = 'Arms' in ob.name
        if not ob.hide_render:
            for mod in list(ob.modifiers):
                if mod.type == 'ARMATURE':
                    ob.modifiers.remove(mod)
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = clay
    elif ob.type == 'LIGHT':
        ob.hide_render = True
cam_data = bpy.data.cameras.new('DetailCamera')
camera = bpy.data.objects.new('DetailCamera', cam_data)
scene.collection.objects.link(camera)
scene.camera = camera
cam_data.type = 'ORTHO'
cam_data.clip_start = .0001
cam_data.clip_end = 10
lamp_data = bpy.data.lights.new('DetailKey', 'AREA')
lamp = bpy.data.objects.new('DetailKey', lamp_data)
scene.collection.objects.link(lamp)
lamp_data.energy = 12
lamp_data.shape = 'DISK'
lamp_data.size = .2
views = [
    ('rear', (-2.7741, 0, 14.1552), (-10, -5, 17), .035),
    ('front', (51.0153, 0, 14.15), (43, -5, 17.5), .035),
    ('muzzle', (70, 0, 5.56), (81, -15, 12), .085),
]
for name, target, eye, scale in views:
    target = point(target)
    camera.location = point(eye)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.ortho_scale = scale
    lamp.location = target + Vector((.10, -.08, .12))
    lamp.rotation_euler = (target - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(O / f'{version}_{name}_clay.png')
    bpy.ops.render.render(write_still=True)
print('SVCH_MECHANISM_CLAY_COMPLETE', version)
