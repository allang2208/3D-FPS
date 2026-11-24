from pathlib import Path
import bpy,math
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'FrontierCompoundBow_R2.blend'))
scene=bpy.context.scene
scene.frame_set(1)
objects={o.name:o for o in scene.objects if o.type=='MESH'}
strings=[]
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler
camera=bpy.data.cameras.new('InventoryCamera');cam=bpy.data.objects.new('InventoryCamera',camera);scene.collection.objects.link(cam)
scene.camera=cam;camera.type='ORTHO';cam.location=(48,-180,44)
center=Vector((1,0,5));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
cam.rotation_euler.rotate_axis('Z',math.radians(62))
points=[o.matrix_world@Vector(v) for o in list(objects.values())+strings for v in o.bound_box]
local=[cam.rotation_euler.to_matrix().inverted()@(v-center) for v in points]
lo=[min(v[i] for v in local) for i in range(2)];hi=[max(v[i] for v in local) for i in range(2)]
cam.location+=cam.rotation_euler.to_matrix()@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
camera.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*2)*1.06;camera.clip_end=600
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Icon studio');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.8,.8,.8,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.85
for pos,energy,size in [((40,-75,80),120000,72),((-25,50,30),82000,62)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=energy;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(light);light.location=pos
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=768;scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(P/'Export/bow_frontier_compound.png')
bpy.ops.render.render(write_still=True)
