import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'))
s=bpy.context.scene
meshes=[o for o in s.objects if o.type=='MESH']
s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=512;s.render.resolution_y=256;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.14,.16,.20,1)
pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];center=sum(pts,Vector())/len(pts)
bpy.ops.object.camera_add(location=center+Vector((1.4,-.1,.25)));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.95;s.camera=cam
for loc,power,size in [((1,-.3,1.4),180,2),((-.8,-.2,.8),120,1.5),((.5,1,.4),80,1)]:
 bpy.ops.object.light_add(type='AREA',location=loc);li=bpy.context.object;li.data.energy=power;li.data.shape='DISK';li.data.size=size;li.rotation_euler=(center-li.location).to_track_quat('-Z','Y').to_euler()
s.render.film_transparent=True;s.render.image_settings.color_mode='RGBA';s.render.filepath=str(O.parents[1]/'Content/ColdSteelData/Icons/ue_qbz191.png');bpy.ops.render.render(write_still=True)
