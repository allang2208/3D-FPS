import bpy
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
a=bpy.data.actions['BeforeThrow_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
s.frame_set(0);bpy.context.view_layer.update();start={b.name:b.matrix_basis.copy() for b in r.pose.bones}
s.frame_set(50);bpy.context.view_layer.update();end={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
for u in [.25,.5,.75]:
 for b in r.pose.bones:
  if b.name.endswith('_l'):
   p,q,z=start[b.name].decompose();P,Q,Z=end[b.name].decompose();b.matrix_basis=Matrix.LocRotScale(p.lerp(P,u),q.slerp(Q,u),z.lerp(Z,u))
 bpy.context.view_layer.update();cam=s.camera;focus=Vector((-.15,-.05,-.22));cam.data.type='ORTHO';cam.data.ortho_scale=1.1;cam.location=focus+Vector((-1,-.1,.27));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100;s.render.filepath=str(O/f'fk_bridge_{u}.png');bpy.ops.render.render(write_still=True)
