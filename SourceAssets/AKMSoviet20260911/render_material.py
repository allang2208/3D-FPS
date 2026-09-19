import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_Soviet_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['AKM_EquipCharge'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(66)
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
w=bpy.data.worlds.new('ReviewWorld');w.use_nodes=True;n=w.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');bg.inputs[0].default_value=(.15,.18,.22,1);bg.inputs[1].default_value=.7;out=n.new('ShaderNodeOutputWorld');w.node_tree.links.new(bg.outputs[0],out.inputs[0]);s.world=w
target=r.matrix_world@(r.pose.bones['hand_l'].matrix.translation.lerp(r.pose.bones['hand_r'].matrix.translation,.5))
for i,off in enumerate([(0,-1,1),(1,.5,1),(-1,0,.4)]):
 d=bpy.data.lights.new('Key'+str(i),'AREA');d.energy=90;d.shape='DISK';d.size=1;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=target+Vector(off);o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('SovietReview');cam=bpy.data.objects.new('SovietReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.8;cam.location=target+Vector((-.5,.35,.25));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'charge_material.png');bpy.ops.render.render(write_still=True)
