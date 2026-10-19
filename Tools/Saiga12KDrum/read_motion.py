"""Production input: saved AKM PalmGripV3 motion on the current Saiga native rig."""
import unreal as u,json,gzip
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDrum20261018'
mesh=u.load_asset('/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.RAW;opts.incorporate_root_motion_into_pose=False
A=u.AnimPoseExtensions
def pack(t):return [getattr(t.translation,c) for c in 'xyz']+[getattr(t.rotation,c) for c in 'xyzw']+[getattr(t.scale3d,c) for c in 'xyz']
result={'sample_rate':120,'clips':{}}
for role in ('drum_reload','drum_reload_empty'):
    clip=u.load_asset('/Game/Weapons/AKMDrumFreeDrop20260920/base/A_AKM_'+role)
    if not clip:raise RuntimeError('Missing PalmGripV3 '+role)
    dur=clip.get_play_length();pose=A.get_anim_pose_at_time(clip,0.,opts);names=[str(n) for n in A.get_bone_names(pose)]
    frames=[]
    for i in range(round(dur*120)+1):
        t=min(i/120.,dur);pose=A.get_anim_pose_at_time(clip,t,opts)
        frames.append({'time':t,'local':{n:pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    result['clips'][role]={'asset':clip.get_path_name(),'duration':dur,'frames':frames}
    print('SAIGA_DRUM_MOTION_INPUT',role,len(frames),flush=True)
with gzip.open(O/'Inputs/reload-source.json.gz','wt',encoding='utf-8') as f:json.dump(result,f)
(O/'Receipts/motion-input.json').write_text(json.dumps({'complete':True,'clips':{k:{'asset':c['asset'],'duration':c['duration'],'frames':len(c['frames'])} for k,c in result['clips'].items()}},indent=2))
