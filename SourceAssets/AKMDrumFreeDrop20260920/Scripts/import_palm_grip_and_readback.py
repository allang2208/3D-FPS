"""Import this pose revision and inspect only its compressed left-finger tracks."""
import unreal as u,json,math,runpy
from pathlib import Path
O=Path(__file__).resolve().parents[1]
project=Path(u.Paths.get_project_file_path()).resolve()
if project != O.parents[1]/'FPSGAME.uproject':raise RuntimeError('This import belongs to FPSGAME: '+str(project))
runpy.run_path(str(O/'Scripts/import_animations.py'),run_name='__main__')
build=json.loads((O/'build_receipt.json').read_text())
contact=json.loads((O/'contact_fit.json').read_text())
source=u.AnimPoseEvaluationOptions();source.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
compressed=u.AnimPoseEvaluationOptions();compressed.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
rows={};peak=0.0
for key,meta in build.items():
 a=u.load_asset(meta['asset']);angles=[];samples=[]
 for frame in (112,178,219):
  raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,frame/120,source)
  runtime=u.AnimPoseExtensions.get_anim_pose_at_time(a,frame/120,compressed)
  entry={}
  for bone in contact['finger_basis']:
   lhs=u.AnimPoseExtensions.get_bone_pose(raw,bone,u.AnimPoseSpaces.LOCAL).rotation
   rhs=u.AnimPoseExtensions.get_bone_pose(runtime,bone,u.AnimPoseSpaces.LOCAL).rotation
   dot=abs(sum(getattr(lhs,c)*getattr(rhs,c) for c in ('x','y','z','w')))
   error=math.degrees(2*math.acos(min(1,max(0,dot))))
   angles.append(error);entry[bone]=[rhs.x,rhs.y,rhs.z,rhs.w]
  samples.append({'frame':frame,'compressed_finger_local_quaternions':entry})
 maximum=max(angles);peak=max(peak,maximum)
 rows[key]={'revision':meta['revision'],'duration':a.get_play_length(),'source_vs_compressed_max_degrees':maximum,'samples':samples}
result={'revision':contact['revision'],'scope':'Left-finger compressed/source poses at pickup and two holding frames, all AKM grip variants; no PIE/gameplay regression','clips':rows,'max_compression_rotation_error_degrees':peak,'game_tested':False}
(O/'Revisions/PalmGripV3/ue_finger_readback.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PALM_GRIP_READBACK_COMPLETE clips='+str(len(rows))+' max_rotation_error_degrees='+str(peak))
