"""Render only the support phase requested for inspection."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Support_Draft.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;cam=s.camera
for f in (280,320,360,400):
    s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
    center=(r.pose.bones['hand_l'].matrix.translation+root@Vector((0,-.16,.04)))/2
    cam.location=center+root.to_3x3()@Vector((.70,.25,.35))
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(O/'Diagnosis'/f'after_{f}.jpg');bpy.ops.render.render(write_still=True)
    if f==320:
        cam.location=center+root.to_3x3()@Vector((-.70,.25,-.12))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(O/'Diagnosis'/'after_320_palm.jpg');bpy.ops.render.render(write_still=True)
