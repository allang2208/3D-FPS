import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
for clip,end in [('reload',126)]:
 a=bpy.data.actions['M4_MAT_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();rest=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix;heldside='l' if clip=='equip_charge' else 'r';held=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_'+heldside].matrix;row={};drift=0;grip=None;gripdrift=0;hook=None;hookdrift=0;seaterror=0;lengths={n:r.pose.bones[n].matrix.translation-r.pose.bones[n].parent.matrix.translation for n in ['lowerarm_l','hand_l','lowerarm_r','hand_r']};lengtherror=0;rows=[]
 for k in range(end*16+1):
  f=k/16;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted();m=inv@r.pose.bones['WPN_SOCKET_Magazine'].matrix;h=inv@r.pose.bones['hand_'+heldside].matrix;drift=max(drift,(h.translation-held.translation).length*1000)
  for n,v in lengths.items():lengtherror=max(lengtherror,abs((r.pose.bones[n].matrix.translation-r.pose.bones[n].parent.matrix.translation).length-v.length)*1000)
  if clip!='equip_charge':
   start,stop,seat,entry=(43,88,80,54) if clip=='reload_empty' else (61,98,95,76)
   if start<=f<=stop:
    g=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@r.pose.bones['hand_l'].matrix
    if grip is None:grip=g
    gripdrift=max(gripdrift,(g.translation-grip.translation).length*1000)
   if f>=seat:seaterror=max(seaterror,(m.translation-rest.translation).length*1000)
   if f in [entry,seat,130,132]:rows.append({'frame':f,'mag_offset_mm':list((m.translation-rest.translation)*1000),'bolt_position_weapon_m':list((inv@r.pose.bones['WPN_bolt'].matrix).translation)})
  elif 12<=f<=19:
   g=r.pose.bones['WPN_ChargingHandle'].matrix.inverted()@r.pose.bones['hand_r'].matrix
   if hook is None:hook=g
   hookdrift=max(hookdrift,(g.translation-hook.translation).length*1000)
 row={'samples_960hz':end*16+1,'held_wrist_drift_mm':drift,'grasp_drift_mm':gripdrift,'hook_drift_mm':hookdrift,'seated_mag_drift_mm':seaterror,'forearm_and_wrist_length_error_mm':lengtherror,'events':rows};report[clip]=row
 assert max(drift,gripdrift,hookdrift)<.5,row
 assert seaterror<.05,row
 assert lengtherror<.1,row
(O/'mechanical_contract.json').write_text(json.dumps(report,indent=2));print('MECHANICAL_CONTRACT_PASS',report)
