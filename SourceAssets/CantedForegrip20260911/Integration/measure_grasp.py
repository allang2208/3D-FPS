import bpy,json,math,itertools
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parents[1]/'VerticalForegrip20260911/Compact75/A_M4_Vertical_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();rest=r.data.bones
H=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((O/'fit_final.json').read_text())['hand_in_root']);L=r.pose.bones['lowerarm_l'].head.copy();U=r.pose.bones['upperarm_l'].head.copy();desired=(H.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized()).normalized();print('BASELINE',math.degrees((H.translation-L).angle(desired)),math.degrees((L-U).angle(H.translation-L)),flush=True)
a=bpy.data.actions['M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();A0=r.pose.bones['upperarm_l'].head.copy();l1=(rest['lowerarm_l'].head_local-rest['upperarm_l'].head_local).length;l2=(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).length;out=[]
Hbase=H.copy();G=Matrix(json.loads((O/'fit_final.json').read_text())['grip_matrix']);pivot=Vector((0,0,-.014));T=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(45),4,'X')@Matrix.Translation(-pivot)
for theta,x,y,z in itertools.product(range(-90,91,15),[.06,.12,.18,.24],[.12,.18,.24,.30],[-.18,-.12,-.06,0]):
 H=G@T@Matrix.Rotation(math.radians(theta),4,'Z')@T.inverted()@G.inverted()@Hbase;desired=(H.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized()).normalized()
 offset=Vector((x,y,z));A=A0+offset;target=H.translation;axis=(target-A).normalized();shift=axis*max(0,(target-A).length-(l1+l2-.015));A+=shift;dist=(target-A).length;axis=(target-A).normalized();natural=target-desired*l2-A;natural-=axis*natural.dot(axis);pole=natural.normalized();along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));bend=math.degrees((target-E).angle(desired));elbow=math.degrees((E-A).angle(target-E));score=max(0,bend-12)**2+offset.length*40+abs(theta)*.12+max(0,42-elbow)**2
 out.append({'axial_degrees':theta,'offset':[x,y,z],'bend':bend,'elbow':elbow,'extra_reach':shift.length,'score':score})
out.sort(key=lambda v:v['score']);(O/'shoulder_candidates.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[:8],indent=2),flush=True)


