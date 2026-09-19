import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish';report={}
m=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative');opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=m;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
def pose(a,f):return u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
def bone(p,n,space=u.AnimPoseSpaces.LOCAL):return u.AnimPoseExtensions.get_bone_pose(p,n,space)
def angle(a,b):return 2*math.acos(min(1,abs(a.x*b.x+a.y*b.y+a.z*b.z+a.w*b.w)))
def distance(a,b):return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)
idle=pose(u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle'),0)
for variant in ['base','prism','angled']:
 for clip in ['reload','reload_empty','drum_reload','drum_reload_empty']:
  name='A_AKM_'+('' if variant=='base' else variant+'_')+clip;a=u.load_asset(P+'/'+variant+'/'+name);assert a
  end=515 if clip.endswith('empty') else 400;assert abs(a.get_play_length()-end/120)<.0001
  worst=0
  for f in range(end+1):
   p=pose(a,f)
   for n in ['index_01_r','index_02_r','index_03_r']:worst=max(worst,angle(bone(p,n).rotation,bone(idle,n).rotation))
  entry={'duration':a.get_play_length(),'index_max_deviation_degrees':math.degrees(worst)};assert worst<.005,entry
  if clip.startswith('drum'):
   points={}
   for f in [0,56,64,76,86]:
    p=pose(a,f);root=bone(p,'WPN_root',u.AnimPoseSpaces.WORLD);mag=bone(p,'WPN_SOCKET_Magazine',u.AnimPoseSpaces.WORLD);points[f]=root.inverse_transform_location(mag.translation)
   entry['extraction_m']={f:distance(v,points[0]) for f,v in points.items()};assert entry['extraction_m'][86]>.12 and entry['extraction_m'][64]>.03,entry
   oldpath='/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_'+clip.replace('drum_','') if variant=='base' else '/Game/Weapons/AKMIntegration/SovietFab/Attachments/'+variant+'/'+name
   old=u.load_asset(oldpath);maxpos=0
   for f in range(120,end+1,2):
    p,q=pose(a,f),pose(old,f)
    for n in ['WPN_root','WPN_SOCKET_Magazine','hand_l','hand_r']:
     maxpos=max(maxpos,distance(bone(p,n,u.AnimPoseSpaces.WORLD).translation,bone(q,n,u.AnimPoseSpaces.WORLD).translation))
   entry['unchanged_tail_max_position_error_cm']=maxpos;assert maxpos<.02,entry
  report[name]=entry
(O/'ue_validation.json').write_text(json.dumps(report,indent=2));u.log('AKM_POLISH_SAVED_VALIDATION_PASS')
