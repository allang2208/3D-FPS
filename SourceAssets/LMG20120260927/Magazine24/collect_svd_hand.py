import json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[2]
mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')
path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload'
clip=u.load_asset(path);opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE)
pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,220/120,opts)
bones=json.loads((O/'sources.json').read_text())['rigs']['201']['bones']
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
names=[n for n in bones if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))]+['WPN_SOCKET_Magazine']
out={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'pose':{n:{'local':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),'world':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))} for n in names}}
(O/'Sources/svd_hand.json').write_text(json.dumps(out,indent=2));print('SVD accepted local hand read')
