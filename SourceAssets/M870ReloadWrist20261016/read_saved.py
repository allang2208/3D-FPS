"""Read the two saved compressed animations after the right-arm repair."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/M870/Tactical20261015/Animations/'
auth=json.loads((O/'authoring.json').read_text());result={}
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
for role,entry in auth['clips'].items():
    path=ROOT+'A_M870_'+role;clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing saved '+path)
    samples=[]
    for f in (0,18,30,44,48,52,58,60,94,344,359,360,390):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,f/60,opt)
        names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose) if str(n).endswith('_r') or str(n) in ('WPN_Shell','WPN_root')]
        samples.append({'frame':f,'world':{n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
    result[role]={'path':path,'length':clip.get_play_length(),'source_hash':u.EditorAssetLibrary.get_metadata_tag(clip,'M870AnimationSourceSHA256'),'expected_source_hash':hashlib.sha256(Path(entry['file']).read_bytes()).hexdigest(),'samples':samples}
(O/'saved_animations.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('M870_WRIST_SAVED_COMPRESSED_POSES_READ',len(result),flush=True)
