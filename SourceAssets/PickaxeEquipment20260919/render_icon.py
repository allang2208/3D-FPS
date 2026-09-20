"""Produce the requested upright inventory artwork from the current pickaxe.

This is the game icon deliverable, not a preview or acceptance render.
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT/'SourceAssets/RusticPickaxe20260919/RusticPickaxe_Fitted_Master.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
center = (low+high)*.5

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'

camera_data = bpy.data.cameras.new('InventoryIcon')
camera_data.type = 'ORTHO'
camera_data.sensor_fit = 'VERTICAL'
camera_data.ortho_scale = max((high.z-low.z)/.92, (high.x-low.x)/((2/3)*.9))
camera = bpy.data.objects.new('InventoryIcon',camera_data)
scene.collection.objects.link(camera)
camera.location = center+Vector((0,-6,0))
camera.rotation_euler = (math.pi/2,0,0)
scene.camera = camera
for name,offset,power in [('Key',(2.5,-3,3.5),620),('Fill',(-3,-1.5,1.2),220),('Rim',(.5,3.5,2.5),330)]:
    data = bpy.data.lights.new(name,'AREA')
    data.energy = power
    data.size = 3
    light = bpy.data.objects.new(name,data)
    scene.collection.objects.link(light)
    light.location = center+Vector(offset)
    light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
world = bpy.data.worlds.new('InventoryIconWorld')
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (.30,.31,.33,1)
background.inputs['Strength'].default_value = .8
scene.world = world
scene.render.filepath = str(HERE/'pickaxe_upright.png')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Pickaxe_Icon_Editable.blend'))
bpy.ops.render.render(write_still=True)
(HERE/'icon_source.json').write_text(json.dumps({'source':str(SOURCE),'icon':scene.render.filepath,
    'resolution':[512,768],'footprint':[2,3],'orientation':'upright, handle down',
    'provenance':'Existing user supplied Meshy pickaxe and packed original PBR materials',
    'runtime_tested':False},indent=2),encoding='utf-8')
print('PICKAXE_UPRIGHT_ICON_AUTHORED',flush=True)
