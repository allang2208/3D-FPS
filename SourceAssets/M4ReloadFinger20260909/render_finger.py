import bpy,math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M4_Reload_FingerCurl.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima']
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o.parent!=rig
    if o.type=='LIGHT':o.hide_render=True
camdata=bpy.data.cameras.new('FingerCamera');cam=bpy.data.objects.new('FingerCamera',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.20;camdata.clip_start=.001
for p in [(1,-1,2),(-1,0,1)]:
    d=bpy.data.lights.new('FingerLight','AREA');d.energy=120;d.size=2;o=bpy.data.objects.new('FingerLight',d)
    scene.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,.3,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
def action(name,t):
    a=bpy.data.actions[name];rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_set(t);bpy.context.view_layer.update()
for t in [60,114]:
    action('M4_reload',t)
    target=(rig.pose.bones['index_01_r'].head+rig.pose.bones['index_03_r'].tail)/2
    cam.location=target+Vector((.18,-.20,.08));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    for label,name in [('before','M4_reload'),('after','M4_reload_FingerCurl')]:
        action(name,t);scene.render.filepath=str(OUT/f'close_{t}_{label}.png');bpy.ops.render.render(write_still=True)
camdata.type='PERSP';camdata.sensor_fit='VERTICAL';camdata.sensor_height=24;camdata.lens=24/(2*math.tan(math.radians(75/2)))
scene.render.resolution_x=1280;scene.render.resolution_y=720
cam.location=(0,-.10,.05);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
for t in [20,60,90,114,150,175]:
    action('M4_reload_FingerCurl',t);scene.render.filepath=str(OUT/f'reload_{t}_after.png');bpy.ops.render.render(write_still=True)
print('M4_RELOAD_FINGER_RENDER_PASS')
