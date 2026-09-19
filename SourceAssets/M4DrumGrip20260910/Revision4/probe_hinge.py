import bpy,math,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision3/M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_HK416_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
for side in ['l','r']:
 names=['upperarm_'+side,'lowerarm_'+side,'hand_'+side];R=[r.data.bones[n].matrix_local.copy() for n in names];P=[r.pose.bones[n].matrix.copy() for n in names];ru=(R[1].translation-R[0].translation).normalized();rv=(R[2].translation-R[1].translation).normalized();rh=ru.cross(rv).normalized();u=(P[1].translation-P[0].translation).normalized();v=(P[2].translation-P[1].translation).normalized();h=u.cross(v).normalized()
 for i,(x,y) in enumerate([(ru,u),(rv,v)]):
  ref=Matrix((x,rh.cross(x),rh)).transposed();tar=Matrix((y,h.cross(y),h)).transposed();q=(tar@ref.transposed()@R[i].to_3x3()).to_quaternion();d=math.degrees(q.rotation_difference(P[i].to_quaternion()).angle);print(side,names[i],'source_difference',min(d,360-d))
 print('hinge_dot_localZ',rh.dot(R[0].to_3x3().col[2]),rh.dot(R[1].to_3x3().col[2]))
