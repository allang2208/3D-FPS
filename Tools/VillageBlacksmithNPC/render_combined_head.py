"""Render the returned Meshy GLB itself with diffuse light and identical framing."""
import math
from pathlib import Path
import bpy
from mathutils import Vector

project = Path(__file__).resolve().parents[2]
root = project / "SourceAssets/VillageBlacksmithNPC20261118/Meshy/CombinedR1"
preview = root / "Review"
preview.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root / 'head.glb'))
s = bpy.context.scene
parts = [ob for ob in s.objects if ob.type == 'MESH']
corners = [ob.matrix_world @ Vector(c) for ob in parts for c in ob.bound_box]
lo = Vector([min(p[i] for p in corners) for i in range(3)])
hi = Vector([max(p[i] for p in corners) for i in range(3)])
center = (lo + hi) * .5
span = hi.z-lo.z
s.render.engine = 'CYCLES'
s.cycles.samples = 28
s.cycles.use_denoising = True
s.render.resolution_x = s.render.resolution_y = 760
s.render.resolution_percentage = 100
s.render.film_transparent = False
s.world = bpy.data.worlds.new('Neutral studio')
s.world.use_nodes = True
world_nodes = s.world.node_tree.nodes
background = world_nodes.get('Background')
background.inputs[0].default_value = (.36,.39,.42,1)
background.inputs[1].default_value = .46
camdata = bpy.data.cameras.new('Orthographic head study')
camera = bpy.data.objects.new(camdata.name,camdata)
s.collection.objects.link(camera)
s.camera = camera
camdata.type = 'ORTHO'
camdata.ortho_scale = span*1.13
camdata.clip_start = span*.004
camdata.clip_end = span*15
def aim(ob,target): ob.rotation_euler = (target-ob.location).to_track_quat('-Z','Y').to_euler()
def light(name, offset, power, radius, color):
    data=bpy.data.lights.new(name,'AREA')
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob)
    ob.location=center+Vector(offset)*span
    data.shape='DISK'; data.size=radius*span
    data.energy=power*span**2;data.color=color
    aim(ob,center)
light('Softbox',(-1.5,-1.8,1.65),130,1.9,(1.0,.95,.88))
light('Sky fill',(1.6,-1.65,.65),68,1.7,(.86,.93,1))
light('Hair rim',(.5,1.5,1.55),155,1.25,(1,.97,.90))
for slug, angle in [('front',0),('three_quarter',-36),('profile',87),('nape',178)]:
    a=math.radians(angle)
    camera.location=center+Vector((math.sin(a)*3,-math.cos(a)*3,.045))*span
    aim(camera,center)
    s.render.filepath=str(preview/(slug+'.png'))
    bpy.ops.render.render(write_still=True)

