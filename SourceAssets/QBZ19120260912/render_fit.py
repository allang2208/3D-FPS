import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
for o in s.objects:o.hide_render=o.name not in ['SK_M4_Infima','SK_Manny_Arms_Export','QBZ191_Export']
print('QBZ_ROOT_SCALE',r.matrix_world,r.pose.bones['WPN_root'].matrix)
for o in list(s.objects):
 if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('QBZPreview');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.15,.17,.2,1)
for kind,f in [('idle',0),('reload',76),('reload',95),('reload_empty',142)]:
 a=bpy.data.actions['QBZ191_'+kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();root=r.matrix_world@r.pose.bones['WPN_root'].matrix;c=root@Vector((0,-.15,0))
 bpy.ops.object.camera_add(location=root@Vector((.85,-.6,.35)));cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.05;s.camera=cam
 lights=[]
 for loc,power in [((1,-.3,1.4),220),((-.8,-.2,.8),180),((.5,1,.4),100)]:
  bpy.ops.object.light_add(type='AREA',location=root@Vector(loc));li=bpy.context.object;li.data.energy=power;li.data.size=1.5;li.rotation_euler=(c-li.location).to_track_quat('-Z','Y').to_euler();lights.append(li)
 s.render.filepath=str(O/f'fit_{kind}_{f}.png');bpy.ops.render.render(write_still=True)
 for o in lights+[cam]:bpy.data.objects.remove(o,do_unlink=True)
