import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Draft.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];cam=s.camera
for f in (296,310,320,350,372):
    s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
    center=(r.pose.bones['hand_r'].matrix.translation+root@Vector((-.025,-.11,.06)))/2
    cam.data.ortho_scale=.47;cam.location=center+root.to_3x3()@Vector((-.70,.28,.30))
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(O/'Diagnosis'/f'after_{f}.jpg');bpy.ops.render.render(write_still=True)
    if f==320:
        cam.location=center+root.to_3x3()@Vector((-.60,-.25,.48));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(O/'Diagnosis/after_320_front.jpg');bpy.ops.render.render(write_still=True)
