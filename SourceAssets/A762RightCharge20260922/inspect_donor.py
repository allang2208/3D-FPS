import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
visible=[]
for ob in s.objects:
    if ob.type=='MESH':
        if not any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers):ob.hide_render=True
        if not ob.hide_render:ob.color=(.26,.45,.65,1) if 'Arms' in ob.name else (.54,.42,.22,1);visible.append(ob.name)
print('VISIBLE',visible,flush=True)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100
s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=83
cam=bpy.data.objects.new('DonorCam',bpy.data.cameras.new('DonorCam'));s.collection.objects.link(cam);s.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=.50
s.frame_set(147);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
center=r.pose.bones['hand_r'].matrix.translation.copy()
cam.location=center+root.to_3x3()@Vector((-.70,.28,.30));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(O/'Diagnosis/ASH12_side.jpg');bpy.ops.render.render(write_still=True)
