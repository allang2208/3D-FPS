import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent/'SourceMatched'
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_MannyNative_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
d=bpy.data.cameras.new('MatchedReview');cam=bpy.data.objects.new('MatchedReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.8
cases=[('idle',0)] if '--idle-only' in sys.argv else [('idle',0),('reload',70),('reload',145),('reload_empty',260),('reload_empty',355)]
for clip,f in cases:
 a=bpy.data.actions['AKM_Native_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 target=r.matrix_world@(r.pose.bones['hand_l'].matrix.translation.lerp(r.pose.bones['hand_r'].matrix.translation,.5))
 for label,offset in [('side',(.65,-.6,.38)),('palm',(-.5,.35,.25))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{clip}_{f}_{label}.png');bpy.ops.render.render(write_still=True)
print('MATCHED_REVIEW_PASS')
