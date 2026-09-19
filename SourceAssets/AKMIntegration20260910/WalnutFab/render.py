import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_WalnutFab_Editable.blend'))
s=bpy.context.scene
for o in s.objects:
 if o.type=='MESH':o.hide_render=not o.name.startswith('AKMR_')
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
s.render.resolution_x=1200;s.render.resolution_y=600;s.render.resolution_percentage=100;s.render.film_transparent=False
s.world=bpy.data.worlds.new('WalnutStudio');s.world.use_nodes=True
wn=s.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.25,.25,.25,1);bg.inputs[1].default_value=.6
points=[o.matrix_world@Vector(c) for o in s.objects if o.type=='MESH' and o.name.startswith('AKMR_') for c in o.bound_box]
target=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))/2
d=bpy.data.cameras.new('WalnutReview');cam=bpy.data.objects.new('WalnutReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=1.03
for j,offset in enumerate([(0.6,-.3,.8),(-.8,.3,.4)]):
 light=bpy.data.lights.new('Softbox'+str(j),'AREA');light.energy=70;light.shape='DISK';light.size=1
 ob=bpy.data.objects.new(light.name,light);s.collection.objects.link(ob);ob.location=target+Vector(offset);ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
for name,offset in [('side',(1,0,.08)),('oblique',(.8,-.45,.4))]:
 cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('WALNUT_RENDER_PASS')
