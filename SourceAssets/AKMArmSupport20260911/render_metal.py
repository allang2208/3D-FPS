import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_OpticMount_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=ob.name not in ['SM_AKM_optic','AKM_Soviet_Native','AKM_FactoryMagazine_Preview']
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
w=bpy.data.worlds.new('MountWorld');w.use_nodes=True;n=w.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');bg.inputs[0].default_value=(.15,.18,.22,1);bg.inputs[1].default_value=.7;out=n.new('ShaderNodeOutputWorld');w.node_tree.links.new(bg.outputs[0],out.inputs[0]);s.world=w
target=r.matrix_world@r.pose.bones['WPN_root'].matrix@Vector((0,-.08,.075))
for i,off in enumerate([(0,-1,1),(1,.5,1),(-1,0,.4)]):
 d=bpy.data.lights.new('MountKey'+str(i),'AREA');d.energy=60;d.shape='DISK';d.size=1;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=target+Vector(off);o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('MountReview');c=bpy.data.objects.new('MountReview',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.43;c.location=target+Vector((-.6,-.25,.25));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'mount_material.png');bpy.ops.render.render(write_still=True);print('AKM_MOUNT_RENDER_PASS')
