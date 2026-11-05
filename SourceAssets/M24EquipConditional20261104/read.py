"""Capture the currently fitted M24 equip and idle for both equip actions."""
from pathlib import Path
import json
import unreal as u
O=Path(__file__).resolve().parent
p=O.parent/'M24QuickMeleeRightHandR3_20261104/read_inputs.py'
code=p.read_text().split('assembly={')[0].replace("('A_M24_idle','A_M24_quick_melee')","('A_M24_idle','A_M24_equip')")
# Sample a whole skeleton at once; repeated per-bone animation evaluation
# is unnecessary for source-pose production.
prefix="""opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=host;opts.evaluation_type=u.AnimDataEvalType.SOURCE
def snapshot(seq,t):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,t,opts)
    return [tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
"""
code=code.replace('clips={};hashes=',prefix+'\nclips={};hashes=').replace('[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,host)]','snapshot(a,i/fps)')
exec(compile(code,'current M24 equip authoring input','exec'))
(O/'input_assets.json').write_text(json.dumps(assets,indent=2));(O/'hashes.json').write_text(json.dumps(hashes,indent=2))
print('M24_EQUIP_INPUTS',len(profiles),len(clips),flush=True)
