"""Read-only inspection of the actually referenced saved SVD animation assets."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
raw=u.AnimPoseEvaluationOptions();raw.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
compressed=u.AnimPoseEvaluationOptions();compressed.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
samples={'idle':[0,5], 'aim':[0,5], 'fire':[0,4,12,36], 'aim_fire':[0,4,12,36], 'equip':[0,20,64,80,94,100,116,176,204], 'reload':[0,24,52,90,110,128,180,220,240,244,252,260,272,298,400], 'reload_empty':[0,52,128,220,240,260,268,298,310,326,344,350,366,432,515], 'inspect':[0,180,360,745], 'quick_melee':[0,20,54,108], 'sprint_enter':[0,24,48], 'sprint_loop':[0,60,120], 'sprint_exit':[0,24,48]}
report={'assets':{},'scope':'Saved animation SOURCE vs COMPRESSED at listed times; no PIE or game startup; no asset writes.'}
for family in ['base','vertical','canted','prism','angled']:
 for clip,frames in samples.items():
  root='/Game/Weapons/SVDDragunov20260922/'+('Complete20260923' if family=='base' else 'Accessories20260923')+'/Animations/'
  path=root+'A_SVD_'+('' if family=='base' else family+'_')+clip
  a=u.load_asset(path)
  if not a:report['assets'][family+'/'+clip]={'missing':path};continue
  length=a.get_play_length();names=list(u.AnimationLibrary.get_animation_track_names(a))
  names=[n for n in names if str(n).startswith(('hand','index','middle','ring','pinky','thumb','clavicle','upperarm','lowerarm','WPN'))]
  row={'path':path,'seconds':length,'source':list(a.get_editor_property('asset_import_data').extract_filenames()),'samples':[]}
  for f in frames:
   t=min(f/120,length);p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,raw);q=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,compressed)
   dp=0;dq=0;wp='';wq=''
   for n in names:
    x=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD);y=u.AnimPoseExtensions.get_bone_pose(q,n,u.AnimPoseSpaces.WORLD)
    v=x.translation-y.translation;d=math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z)*10
    dot=abs(x.rotation.x*y.rotation.x+x.rotation.y*y.rotation.y+x.rotation.z*y.rotation.z+x.rotation.w*y.rotation.w)
    angle=2*math.acos(min(1,dot))*180/math.pi
    if d>dp:dp=d;wp=str(n)
    if angle>dq:dq=angle;wq=str(n)
   row['samples'].append({'frame':f,'seconds':t,'max_position_error_mm':dp,'position_bone':wp,'max_rotation_error_deg':dq,'rotation_bone':wq})
  report['assets'][family+'/'+clip]=row
  (O/'ue_readback.json').write_text(json.dumps(report,indent=2))
  print('SVD_AUDIT_READ',family,clip,length,flush=True)
print('SVD_AUDIT_UE_DONE',len(report['assets']),flush=True)
