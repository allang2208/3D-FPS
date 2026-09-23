"""Measure pose-space finger segment lengths and rigid contact relationships."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'SVDAttachments20260923';report={}
for family in ['base','vertical','canted','prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(S/('SVD_Modular_Editable.blend' if family=='base' else 'SVD_'+family+'_Editable.blend')))
 r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');s=bpy.context.scene
 def pose(clip,f):
  a=bpy.data.actions['A_SVD_'+('' if family=='base' else family+'_')+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
 idle=pose('idle',0);rows=[]
 for clip,frames in {'idle':[0], 'equip':[20,42,64,80,90,94,100,116,150,176], 'reload':[0,52,90,110,128,180,220,240,244,252,260,272,298,400], 'reload_empty':[128,220,240,268,310,326,340,344,350,366,432,515], 'quick_melee':[0,20,54,108], 'sprint_enter':[0,24,48],'sprint_exit':[0,24,48]}.items():
  for f in frames:
   p=pose(clip,f);finger={}
   for side in ['l','r']:
    values=[]
    for b in r.data.bones:
     n=b.name
     if not (n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')) and b.parent):continue
     parent=b.parent.name;rest=(b.matrix_local.translation-b.parent.matrix_local.translation).length;length=(p[n].translation-p[parent].translation).length
     local=p[parent].inverted()@p[n];neutral=b.parent.matrix_local.inverted()@b.matrix_local
     values.append({'bone':n,'rest_length_mm':rest*1000,'posed_length_mm':length*1000,'ratio':length/max(rest,1e-8),'local_translation_delta_mm':(local.translation-neutral.translation).length*1000})
    finger[side]=sorted(values,key=lambda x:x['local_translation_delta_mm'],reverse=True)
   rows.append({'clip':clip,'frame':f,'fingers':finger,'left_hand_in_mag':[list(x) for x in p['WPN_SOCKET_Magazine'].inverted()@p['hand_l']], 'right_hand_in_bolt':[list(x) for x in p['WPN_bolt'].inverted()@p['hand_r']], 'idle_return':{n:{'position_mm':(p[n].translation-idle[n].translation).length*1000,'rotation_deg':p[n].to_quaternion().rotation_difference(idle[n].to_quaternion()).angle*180/math.pi} for n in ['hand_l','hand_r','WPN_root','WPN_SOCKET_Magazine']}})
 report[family]=rows
(O/'bone_tracks.json').write_text(json.dumps(report,indent=2));print('SVD_AUDIT_BONE_TRACKS_DONE',flush=True)
