import bpy, math
from pathlib import Path
from mathutils import Vector
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\ArmsReplacement')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SK_ArmsReplacement_Source.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
for ob in list(bpy.data.objects):
    if ob.type in ('LIGHT','CAMERA'): bpy.data.objects.remove(ob,do_unlink=True)
s.world.color=(.025,.030,.040)
rig=bpy.data.objects['SK_AKM_Viewmodel']
cdata=bpy.data.cameras.new('ArmsReplacementCamera');cam=bpy.data.objects.new('ArmsReplacementCamera',cdata);bpy.context.collection.objects.link(cam);s.camera=cam
cam.location=(.85,-1.25,.37);center=Vector((0,.22,-.20));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cdata.lens=54
for name,pos,power,size in [('Key',(.6,-.4,.9),95,1.1),('Fill',(-.7,-.25,.35),65,1.5),('Rim',(.25,.9,.65),110,1.2)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
s.view_settings.look='AgX - Medium High Contrast'
for actname,frame in [('idle',1),('reload',24),('reload_empty',52)]:
    a=bpy.data.actions['AKM_'+actname];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
    s.render.filepath=str(OUT/('arms_replacement_'+actname+'.png'));bpy.ops.render.render(write_still=True)
print('ARMS_REPLACEMENT_PREVIEWS_READY')
