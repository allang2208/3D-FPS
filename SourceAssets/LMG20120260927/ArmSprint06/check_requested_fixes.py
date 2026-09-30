"""Focused read-back of authored assets for the two user-reported defects."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;P=O.parent/'Support05';C=O.parent/'Charging04'
meta=json.loads((O/'motion_authoring.json').read_text());out={'scope':'source animation read-back for left-arm twist, sprint release and boundaries','clips':{},'runtime_tested':False,'visual_tested':False}
def read(path,times):
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=bpy.context.scene;fps=sc.render.fps/sc.render.fps_base;rows=[]
 for t in times:
  f=t*fps;sc.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return rows,{b.name:b.matrix_local.copy() for b in r.data.bones}
def error(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
def qangle(a,b):return math.degrees(2*math.acos(min(1,abs(a.to_quaternion().normalized().dot(b.to_quaternion().normalized())))))
edges={};worst_keep=worst_contact=worst_profile=0.0
for key,d in meta['animations'].items():
 times=[i/d['fps'] for i in range(d['frames'])];new,rest=read(O/'Motions'/f'A_LMG201_{key}.blend',times);old,_=read(P/'Motions'/f'A_LMG201_{key}.blend',times)
 sprint=key.startswith('sprint_');reference,_=read(C/'Motions'/f'A_LMG201_{key}.blend',times) if not sprint else (None,None)
 keep=contact=profile=0.;helper_angles={};fore_lengths=[]
 for j,(a,b) in enumerate(zip(new,old)):
  for n in a:
   if n.endswith('_r') or n.startswith('WPN_'):keep=max(keep,error(a[n],b[n]))
   if not sprint and n.endswith('_l') and n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')):contact=max(contact,error(a[n],b[n]))
  for prefix in ['upperarm','lowerarm']:
   bn=prefix+'_l'
   for suffix in ['01','02']:
    n=prefix+'_twist_'+suffix+'_l'
    if n not in a:continue
    if reference:
     ref=reference[j];profile=max(profile,error(a[bn].inverted()@a[n],ref[bn].inverted()@ref[n]))
    helper_angles[n]=qangle(a[n]@rest[n].inverted(),a[bn]@rest[bn].inverted())
  fore_lengths.append((a['hand_l'].translation-a['lowerarm_l'].translation).length)
 first,last=new[0],new[-1];edges[key]=(first,last)
 row={'preserved_right_weapon_matrix_error':keep,'non_sprint_hand_contact_matrix_error':contact if not sprint else None,'native_helper_relation_error':profile if not sprint else None,'forearm_length_range_m':[min(fore_lengths),max(fore_lengths)],'helper_degrees_at_end':helper_angles}
 if sprint:
  row['wrist_start_m']=list(first['hand_l'].translation);row['wrist_end_m']=list(last['hand_l'].translation)
  row['wrist_below_shoulder_at_end_m']=last['upperarm_l'].translation.z-last['hand_l'].translation.z
  row['local_wrist_rest_angle_end_deg']=qangle(last['lowerarm_l'].inverted()@last['hand_l'],rest['lowerarm_l'].inverted()@rest['hand_l'])
 out['clips'][key]=row;worst_keep=max(worst_keep,keep);worst_contact=max(worst_contact,contact);worst_profile=max(worst_profile,profile)
 print('CHECKED_SOURCE',key,'preserved',keep,'hand_contact',contact,'native_profile',profile,flush=True)
left=[n for n in edges['idle'][0] if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand_','thumb_','index_','middle_','ring_','pinky_'))]
joins=[('idle_to_enter',edges['idle'][0],edges['sprint_enter'][0]),('enter_to_loop',edges['sprint_enter'][1],edges['sprint_loop'][0]),('loop_seam',edges['sprint_loop'][0],edges['sprint_loop'][1]),('loop_to_exit',edges['sprint_loop'][0],edges['sprint_exit'][0]),('exit_to_idle',edges['sprint_exit'][1],edges['idle'][0])]
out['left_sprint_join_errors']={name:max(error(a[n],b[n]) for n in left) for name,a,b in joins}
out['maximums']={'right_weapon_error':worst_keep,'holding_contact_error':worst_contact,'native_helper_profile_error':worst_profile}
out['sprint_withdrawal_distance_m']=(edges['sprint_enter'][0]['hand_l'].translation-edges['sprint_enter'][1]['hand_l'].translation).length
out['status']='source_checks_completed; no runtime or visual acceptance'
(O/'focused_source_checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('201_REQUESTED_SOURCE_CHECKS',json.dumps({'maximums':out['maximums'],'joins':out['left_sprint_join_errors'],'withdrawal_m':out['sprint_withdrawal_distance_m']}),flush=True)
if worst_keep>1e-4 or worst_contact>1e-4 or worst_profile>1e-4 or max(out['left_sprint_join_errors'].values())>1e-4:raise RuntimeError('Source boundary/preservation error; repair before import')
print('201_REQUESTED_SOURCE_CHECKS_COMPLETE',flush=True)
