import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=u.load_asset(P+'/Attachments/SK_AKM_MannyNative');report={}
for variant in ['prism','angled']:
 for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']:
  name=f'A_AKM_{variant}_{clip}';a=u.load_asset(P+('/GripReturn/' if 'reload' in clip else '/Attachments/')+variant+'/'+name);tracks={}
  for f in range(round(a.get_play_length()*120)+1):
   p=u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
   for n in u.AnimPoseExtensions.get_bone_names(p):
    n=str(n)
    if not (n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))):continue
    t=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL);v,q,s=t.translation,t.rotation,t.scale3d;tracks.setdefault(n,[]).append([[v.x,v.y,v.z],[q.x,q.y,q.z,q.w],[s.x,s.y,s.z]])
  report[name]=tracks
(O/'installed_digit_tracks.json').write_text(json.dumps(report));u.log('AKM_DIGIT_SNAPSHOT_PASS')
