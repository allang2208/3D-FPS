import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(r'D:\FPS3D\FPSGAME');src=root/'SourceAssets/AxeHitPause20260919/Axe_HitPause_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));r=bpy.data.objects['SK_Harvest_Axe_Rig'];s=bpy.context.scene;a=bpy.data.actions['A_Harvest_Axe_HitRecover'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
rest={b.name:b.matrix_local.copy() for b in r.data.bones};u='upperarm_r';f='lowerarm_r';h='hand_r';ur=(rest[f].translation-rest[u].translation).normalized();fr=(rest[h].translation-rest[f].translation).normalized()
rows=[]
for age in (0,.2,.23,.3,.42,.51,.64,.8,.92):
 frame=age/.92*.44*300;s.frame_set(math.floor(frame),subframe=frame-math.floor(frame));p={b.name:b.matrix.copy() for b in r.pose.bones};up=(p[f].translation-p[u].translation).normalized();fo=(p[h].translation-p[f].translation).normalized();uq=p[u].to_quaternion()@rest[u].to_quaternion().inverted();hq=p[h].to_quaternion()@rest[h].to_quaternion().inverted();fq=(hq@fr).rotation_difference(fo)@hq;carry=(uq@fr).rotation_difference(fo)@uq;delta=fq@carry.inverted();roll=(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(fo),delta.w)+math.pi)%(2*math.pi)-math.pi
 rows.append({'age':age,'shoulder':list(p[u].translation),'elbow':list(p[f].translation),'wrist':list(p[h].translation),'elbow_bend_deg':math.degrees(up.angle(fo)),'wrist_swing_deg':math.degrees((hq@fr).angle(fo)),'segment_roll_deg':math.degrees(roll)})
report={'source':str(src),'rest':{n:[list(x) for x in rest[n]] for n in ('clavicle_r',u,f,h)},'poses':rows};(root/'SourceAssets/AxeRightArm20260919/source_pose.json').write_text(json.dumps(report,indent=2));print('AUTHOR_INPUT',json.dumps(rows),flush=True)
