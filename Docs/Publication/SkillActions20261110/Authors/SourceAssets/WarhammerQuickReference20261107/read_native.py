"""Read the saved V9-compatible animation data model as authoring input."""
from pathlib import Path
import unreal as u
import json
P=Path(__file__).resolve().parent
seq=u.load_asset('/Game/Weapons/SteelWarhammer20261014/QuickCombatLeftWristV7/A_Warhammer_QuickCombat')
names=[str(n) for n in seq.get_editor_property('data_model_interface').get_bone_track_names()]
out={}
for n,tf in zip(names,u.AnimationLibrary.get_bone_poses_for_time(seq,names,0.,False)):
    p,q,s=tf.translation,tf.rotation,tf.scale3d
    out[n]=dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])
(P/'native-idle.json').write_text(json.dumps(dict(bones=out,skeleton=seq.get_editor_property('skeleton').get_path_name())))
print('HAMMER_NATIVE_INPUTS',len(out))
