"""Targeted imported raw/compressed pose check; no gameplay/save manipulation."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';mesh=u.load_asset(P+'/SK_PKM_Manny');report={}
def parts(t):
 q=t.rotation;v=t.translation
 return {'translation':[v.x,v.y,v.z],'rotation':[q.x,q.y,q.z,q.w]}
for mode in [u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED]:
 opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=mode;opt.optional_skeletal_mesh=mesh
 for clip,times in [('idle',[0,.5,1]),('reload',[0,1.3,6.5]),('reload_empty',[0,1.3,7.5])]:
  anim=u.load_asset(P+'/Animations/A_PKM_'+clip)
  for time in times:
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,time,opt);row={}
   for bone in ['PKM_Cover','PKM_Box','PKM_BoxLid','New_PKM_Box','New_PKM_BoxLid']:
    p=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL);ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
    q=p.rotation;qr=ref.rotation;dot=abs(q.x*qr.x+q.y*qr.y+q.z*qr.z+q.w*qr.w)
    row[bone]={'pose':parts(p),'ref':parts(ref),'rotation_from_rest_deg':math.degrees(2*math.acos(min(1,max(-1,dot))))}
    if clip=='idle' and bone in ['PKM_Cover','PKM_Box','PKM_BoxLid']:
     if row[bone]['rotation_from_rest_deg']>.1:raise RuntimeError('Idle rest-axis regression: '+bone+' '+str(row[bone]))
     if (p.translation-ref.translation).length()>.01:raise RuntimeError('Idle part displaced from mount: '+bone)
   report[str(mode)+':'+clip+':'+str(time)]=row
(O/'imported_pose_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PKM imported raw/compressed pose samples saved.')
