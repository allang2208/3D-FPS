"""Production input: saved AKM PalmGripV3 motion on the current Saiga native rig."""
import unreal as u,json,gzip
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KReloadReturn20261018'
mesh=u.load_asset('/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.RAW;opts.incorporate_root_motion_into_pose=False
A=u.AnimPoseExtensions
def pack(t):return [getattr(t.translation,c) for c in 'xyz']+[getattr(t.rotation,c) for c in 'xyzw']+[getattr(t.scale3d,c) for c in 'xyz']
result={'sample_rate':120,'clips':{}}
for role in ('reload_empty','drum_reload_empty'):
    clip=u.load_asset(('/Game/Weapons/AKMDrumFreeDrop20260920/base/A_AKM_' if role.startswith('drum') else '/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_')+role)
    if not clip:raise RuntimeError('Missing PalmGripV3 '+role)
    dur=clip.get_play_length();pose=A.get_anim_pose_at_time(clip,0.,opts);names=[str(n) for n in A.get_bone_names(pose)]
    frames=[]
    for i in range(round(dur*120)+1):
        t=min(i/120.,dur);pose=A.get_anim_pose_at_time(clip,t,opts)
        frames.append({'time':t,'local':{n:pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    result['clips'][role]={'asset':clip.get_path_name(),'duration':dur,'frames':frames}
    print('SAIGA_RETURN_MOTION_INPUT',role,len(frames),flush=True)

result['profiles']={}
for family in ('base','drum','angled','vertical','canted','prism'):
 path='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_'+family
 profile=u.load_asset(path);clips=[]
 for c in profile.get_editor_property('clips'):
  base=c.get_editor_property('base');retained=c.get_editor_property('retained')
  clips.append({'base':base.get_path_name(),'duration':c.get_editor_property('duration'),'retained':retained.get_path_name() if retained else None,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
 result['profiles'][family]={'path':path,'family':family,'clips':clips}
idle=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle')
pose=A.get_anim_pose_at_time(idle,0.,opts)
result['idle']={n:pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}
result['reference']={n:pack(A.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
result['mesh']=mesh.get_path_name()
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=sub.get_game_world();result['editor']={'world':w.get_path_name() if w else None,'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
with gzip.open(O/'Inputs/reload-source-scoped.json.gz','wt',encoding='utf-8') as f:json.dump(result,f)
(O/'Receipts/motion-input-scoped.json').write_text(json.dumps({'complete':True,'editor':result['editor'],'clips':{k:{'asset':c['asset'],'duration':c['duration'],'frames':len(c['frames'])} for k,c in result['clips'].items()}},indent=2))
print('SAIGA_RETURN_INPUT_SAVED',result['editor'],flush=True)
