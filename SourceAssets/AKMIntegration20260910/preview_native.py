import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent/'Native'
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_MannyNative_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
print('CAMERAS',[(o.name,list(o.location)) for o in s.objects if o.type=='CAMERA'])
for o in s.objects:
 if o.type=='LIGHT':o.hide_render=True
s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
s.world.color=(.2,.2,.2)
for i,loc in enumerate([(1,-1,2),(-1,-.5,1),(0,1,2)]):
 d=bpy.data.lights.new('AKM_preview_'+str(i),'AREA');d.energy=150;d.shape='DISK';d.size=2;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.3))-o.location).to_track_quat('-Z','Y').to_euler()
c=bpy.data.cameras.new('AKM_Review');cam=bpy.data.objects.new('AKM_Review',c);s.collection.objects.link(cam);s.camera=cam;c.lens=40
for name,f in [('idle',0),('reload',148),('reload_empty',280)]:
 a=bpy.data.actions['AKM_Native_'+name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 target=r.matrix_world@r.pose.bones['WPN_root'].matrix.translation
 cam.location=target+Vector((.8,-.8,.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
