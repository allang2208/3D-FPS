"""Read full current native poses to preserve the complete editable source."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/HK416ReloadGrip20261001');P=O.parents[1];I=O/'Inputs'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():raise RuntimeError('Wrong project')
index=json.loads((O/'inputs.json').read_text());bind=json.loads((I/'bind.json').read_text());mesh=u.load_asset(index['mesh'])
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.RAW
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for key,spec in index['clips'].items():
 file=I/(spec['family']+'__'+spec['kind']+'__full.json.gz')
 if file.exists():continue
 disk=P/'Content'/(key.removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=spec['sha256']:raise RuntimeError('Source changed '+key)
 a=u.load_asset(key);times=[u.AnimationLibrary.get_time_at_frame(a,f) for f in range(u.AnimationLibrary.get_num_frames(a)+1)];world=[]
 for t in times:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts)
  world.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bind['names']])
 with gzip.open(file,'wt',encoding='utf8') as f:json.dump({'asset':key,'times':times,'bones':bind['names'],'world':world},f,separators=(',',':'))
 print('HK416_EDITABLE_SOURCE',spec['family'],spec['kind'],flush=True)
