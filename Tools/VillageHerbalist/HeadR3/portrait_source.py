"""Photograph the generated bare head before the separate eyeglass mesh is fitted."""
from pathlib import Path
import math
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
HEAD = ROOT / "SourceAssets/VillageHerbalist/FullBody/HeadR3"
OUT = HEAD / "Review/BareHead"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HEAD / "Meshy/head.glb"))
scene = bpy.context.scene
objects = [o for o in scene.objects if o.type == "MESH"]
points = np.array([tuple(o.matrix_world @ p.co) for o in objects for p in o.data.vertices])
low, high = points.min(0), points.max(0)
height = high[2]-low[2]
target = Vector(((high[0]+low[0])*.5, (high[1]+low[1])*.5, low[2]+height*.52))
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 5
scene.render.resolution_x = scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('Studio bounce')
scene.world.use_nodes = True
world = scene.world.node_tree
bg = next(n for n in world.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (.68,.66,.62,1.)
bg.inputs['Strength'].default_value = .55
def aim(obj):
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name, off, size, energy):
    light = bpy.data.lights.new(name,'AREA')
    light.shape='DISK'
    light.size = size*height
    light.energy = energy*height*height
    obj=bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location=target+Vector(off)*height
    aim(obj)
area('Window key',(-.90,-1.45,1.0),1.45,72.)
area('Fill',(.95,-.8,.30),1.20,25.)
area('Rear softbox',(.60,.95,.75),1.15,32.)
camera=bpy.data.objects.new('Portrait camera',bpy.data.cameras.new('Portrait'))
scene.collection.objects.link(camera)
scene.camera=camera
camera.data.type='ORTHO'
camera.data.ortho_scale=height*1.10
camera.data.clip_start=height*.003
camera.data.clip_end=height*12
for view,degrees in [('front',0),('three-quarter',38)]:
    turn=math.radians(degrees)
    camera.location=target+Vector((math.sin(turn),-math.cos(turn),0.))*height*3.
    aim(camera)
    scene.render.filepath=str(OUT/(view+'.png'))
    bpy.ops.render.render(write_still=True)
