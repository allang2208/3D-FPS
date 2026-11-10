"""Read current animation data-model grip anchors; no playback or tests."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
names=list(json.loads((P.parent/'SwordUppercut20261003/GripRecoveryV15/inputs.json').read_text())['parents'])
out={}
for grip,folder in [('Standard','/Game/Weapons/AzureRunesword20260913'),('LongGrip','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    seq=u.load_asset(folder+'/A_RuneSword_Idle')
    transforms=u.AnimationLibrary.get_bone_poses_for_time(seq,names,0.,False)
    rows={}
    for name,tf in zip(names,transforms):
        p,q,s=tf.translation,tf.rotation,tf.scale3d
        rows[name]=dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])
    out[grip]=dict(idle=rows,skeleton=seq.get_editor_property('skeleton').get_path_name(),source=seq.get_path_name())
(P/'grip_poses.json').write_text(json.dumps(out))
print('CHAIN_SLASH_ANCHORS_SAVED',list(out))
