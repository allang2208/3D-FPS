import bpy,json,math
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
for clip in ['reload','reload_empty','equip_charge','drum_reload','drum_reload_empty']:
 a=bpy.data.actions['M4_MAT_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];prev={};worst=[];rigid=0
 source=bpy.data.actions[('A_M4_HK416_' if clip.startswith('drum') else 'M4_HK416_')+clip];old=[]
 for f in range(round(a.frame_range[1])+1):
  r.animation_data.action=source;r.animation_data.action_slot=source.slots[0];s.frame_set(f);bpy.context.view_layer.update();old.append({b.name:b.matrix.copy() for b in r.pose.bones if b.name.startswith('WPN_')})
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for f in range(round(a.frame_range[1])*2+1):
  s.frame_set(f//2,subframe=(f%2)*.5);bpy.context.view_layer.update()
  for b in r.pose.bones:
   if b.name.startswith('WPN_') and f%2==0:rigid=max(rigid,max(abs(b.matrix[i][j]-old[f//2][b.name][i][j]) for i in range(4) for j in range(4)))
   if b.name.startswith(('hand_','lowerarm_','upperarm_','index_','middle_','thumb_','ring_','pinky_')):
    q=b.matrix_basis.to_quaternion()
    if b.name in prev:
     angle=math.degrees(prev[b.name].rotation_difference(q).angle);angle=min(angle,360-angle);worst.append((angle,b.name,f/2))
    prev[b.name]=q.copy()
 worst.sort(reverse=True);report[clip]={'max_weapon_matrix_error':rigid,'largest_half_frame_rotation_deg':worst[:12]}
(O/'deformation_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
