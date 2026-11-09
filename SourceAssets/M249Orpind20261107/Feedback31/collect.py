"""Read current M249 reloads and reference rifle receiver motion; no writes."""
from pathlib import Path
import unreal as u,pickle,json,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2]
d=pickle.load(open(r.parent/'Repair20/native.pkl','rb'));d['clips']={};hashes={}
def record(a):
 p=a.get_path_name().split('.')[0];hashes[p]=hashlib.sha256((project/'Content'/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');record(mesh)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
for family,p in d['profiles'].items():
 a=u.load_asset(p['asset']);record(a);rows=[]
 for c in a.get_editor_property('clips'):
  v=c.get_editor_property;retained=v('retained')
  rows.append(dict(base=v('base').get_path_name(),retained=retained.get_path_name()if retained else None,duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values')))for t in v('tracks')]))
 p['clips']=rows
paths=sorted({c['base'].split('.')[0]for p in d['profiles'].values()for c in p['clips']if c['base'].split('.')[-1].endswith(('_reload','_reload_empty'))})
for path in paths:
 clip=u.load_asset(path);record(clip);duration=clip.get_play_length();times=[min(i/120,duration)for i in range(round(duration*120)+1)];rows=[]
 for t in times:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
  rows.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL))for n in d['names']])
 d['clips'][clip.get_path_name()]=dict(fps=120,duration=duration,times=times,frames=rows,root_motion=clip.get_editor_property('enable_root_motion'))
 print('FEEDBACK31_READ',path,flush=True)
pickle.dump(d,open(r/'current.pkl','wb'))
pie='-run='not in u.SystemLibrary.get_command_line().lower()and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
dirty=[p.get_path_name()for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(r/'inputs.json').write_text(json.dumps(dict(pie=pie,dirty=dirty,hashes=hashes,clips=paths),indent=2))
refs={}
for key,meshpath,paths in [
 ('M4','/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',['/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload','/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty']),
 ('PKM','/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',['/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload','/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload_empty'])]:
 opt.optional_skeletal_mesh=u.load_asset(meshpath)
 for path in paths:
  clip=u.load_asset(path)
  if not clip:raise RuntimeError('Reference not found: '+path)
  duration=clip.get_play_length();times=[min(i/60,duration)for i in range(round(duration*60)+1)];rows=[]
  for t in times:
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt);rows.append(tr(u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)))
  refs[key+'/'+clip.get_name()]=dict(path=path,times=times,frames=rows)
(r/'references.json').write_text(json.dumps(refs))
print('FEEDBACK31_COMPLETE',len(d['clips']),len(d['profiles']),'PIE',pie,flush=True)
