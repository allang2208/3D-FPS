import bpy,json
from mathutils import Vector
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/AKMBridgeRefine20260911')
bpy.ops.wm.open_mainfile(filepath=str(O/'prism_scope_2x_AKM_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];root=r.matrix_world@r.pose.bones['WPN_root'].matrix
obj=bpy.data.objects['AKM_Soviet_Native'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();vs=[root.inverted()@ev.matrix_world@v.co for v in mesh.vertices];vs=[v for v in vs if -.14<v.y<-.07 and .066<v.z<.095];print('RECEIVER_X',min(v.x for v in vs),max(v.x for v in vs))
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100
c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=.22;t=root@Vector((0,-.105,.083));c.location=root@Vector((.3516,-.065,.19));c.rotation_euler=(t-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'left-review.png');bpy.ops.render.render(write_still=True)
