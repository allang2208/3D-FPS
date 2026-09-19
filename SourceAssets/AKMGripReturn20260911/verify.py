import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset(P+'/Attachments/SK_AKM_MannyNative');opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;report={}
def pose(a,f):return u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
def world(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
def wrist(p):return world(p,'WPN_root').inverse_transform_location(world(p,'hand_l').translation)
def dist(a,b):return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)
for variant in ['prism','angled']:
 idle=u.load_asset(P+f'/Attachments/{variant}/A_AKM_{variant}_idle');target=wrist(pose(idle,0))
 for clip in ['reload','reload_empty','drum_reload','drum_reload_empty']:
  name=f'A_AKM_{variant}_{clip}';a=u.load_asset(P+'/GripReturn/'+variant+'/'+name);old=u.load_asset(P+'/ReloadPolish/'+variant+'/'+name);empty='empty' in clip;start,finish,end=(380,440,515) if empty else (270,330,400)
  assert a and abs(a.get_play_length()-end/120)<.0001
  maximum=max(dist(wrist(pose(a,f)),target) for f in range(finish,end+1));assert maximum<.003, (name,maximum)
  unchanged=0
  for f in range(0,start+1,2):
   p,q=pose(a,f),pose(old,f)
   for n in ['hand_l','hand_r','WPN_root','WPN_SOCKET_Magazine']:unchanged=max(unchanged,dist(world(p,n).translation,world(q,n).translation))
  assert unchanged<.03,(name,unchanged)
  report[name]={'duration':a.get_play_length(),'return_start_frame':start,'grip_held_from_frame':finish,'held_wrist_max_error_m':maximum,'preserved_initial_action_error_cm':unchanged}
(O/'ue_validation.json').write_text(json.dumps(report,indent=2));u.log('AKM_GRIP_RETURN_VALIDATION_PASS')
