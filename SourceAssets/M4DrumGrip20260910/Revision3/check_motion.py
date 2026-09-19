import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
report={}
for clip,end in [('reload',126),('reload_empty',162)]:
 a=bpy.data.actions['A_M4_DrumGrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 names=['upperarm_l','lowerarm_l','hand_l','lowerarm_twist_01_l','lowerarm_twist_02_l','WPN_SOCKET_Magazine']
 maxima={n:{'rotation_step_deg':0,'rotation_frame':0,'distance_step_cm':0,'local_translation_cm':0,'location_frame':0} for n in names};prev={};max_scale=0;max_translation=0
 for t in range(end*2+1):
  s.frame_set(t//2,subframe=(t%2)*.5);bpy.context.view_layer.update()
  for n in names:
   b=r.pose.bones[n];m=b.matrix_basis.copy();q=m.to_quaternion();p=b.head.copy()
   if m.translation.length*100>maxima[n]['local_translation_cm']:maxima[n]['local_translation_cm']=m.translation.length*100;maxima[n]['location_frame']=t/2
   if n in prev:
    oldq,oldp=prev[n];angle=math.degrees(oldq.rotation_difference(q).angle);angle=min(angle,360-angle)
    if angle>maxima[n]['rotation_step_deg']:maxima[n]['rotation_step_deg']=angle;maxima[n]['rotation_frame']=t/2
    maxima[n]['distance_step_cm']=max(maxima[n]['distance_step_cm'],(p-oldp).length*100)
   prev[n]=(q,p)
   if n!='WPN_SOCKET_Magazine':max_translation=max(max_translation,m.translation.length*100);max_scale=max(max_scale,(m.to_scale()-Vector((1,1,1))).length)
 report[clip]={'half_frame_steps':maxima,'max_local_translation_cm':max_translation,'max_scale_delta':max_scale}
print(json.dumps(report,indent=2));(O/'continuity_report.json').write_text(json.dumps(report,indent=2))
