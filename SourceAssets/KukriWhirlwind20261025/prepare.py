"""Read the original local CC0 C take for native third-person authoring."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'KukriThirdPerson20261024/ComboV3'
cached=json.loads((BASE/'inputs.json').read_text())
source=cached['source']
prefix='/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Donor/'
mesh=u.load_asset(source['mesh'])
clip=u.load_asset(prefix+'A_UAL2_Armature_Sword_Regular_C')
if not isinstance(clip,u.AnimSequence):raise RuntimeError('Original Sword Regular C is unavailable')
opt=u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh=mesh
opt.evaluation_type=u.AnimDataEvalType.SOURCE

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

length=clip.get_play_length()
frames=[]
for i in range(round(length*60)+1):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,length),opt)
    frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in source['names']])
(OUT/'source-c.json').write_text(json.dumps(dict(asset=clip.get_path_name(),duration=length,rate=60,names=source['names'],frames=frames),separators=(',',':')))
print('KUKRI_WHIRLWIND_C_SOURCE_SAVED '+str(length),flush=True)
