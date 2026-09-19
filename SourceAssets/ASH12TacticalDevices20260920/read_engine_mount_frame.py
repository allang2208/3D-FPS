"""Compare the actual imported reference frame with the Blender authoring frame."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.AnimPoseExtensions;M=u.MathLibrary
mesh=u.load_asset('/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface')
clip=u.load_asset('/Game/Weapons/ASH12/Integrated20260917/Animations/A_ASH12_idle')
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
p=E.get_anim_pose_at_time(clip,0,options)
def v(a):return [a.x,a.y,a.z]
def q(a):return [a.x,a.y,a.z,a.w]
def t(a):return {'position':v(a.translation),'rotation':q(a.rotation),'scale':v(a.scale3d)}
names=('WPN_root','WPN_RearSight','WPN_FrontSight')
bones={n:E.get_ref_bone_pose(p,n,u.AnimPoseSpaces.WORLD) for n in names}
root,rear,front=[bones[n] for n in names]
rotation=M.make_rot_from_xz(front.translation-rear.translation,M.get_up_vector(rear.rotation.rotator()))
frame=u.Transform(location=rear.translation,rotation=rotation)
position=M.transform_location(frame,u.Vector(29.5,-3.19,-8.25))
mount=u.Transform(location=position,rotation=(rotation.quaternion()*u.Quat(1,0,0,0)).rotator())
relative=M.make_relative_transform(mount,root)
out={'reference':{n:t(x) for n,x in bones.items()},'sight_frame':t(frame),'mount_component':t(mount),'mount_root_relative':t(relative)}
(O/'engine_mount_frame.json').write_text(json.dumps(out,indent=2))
print('ASH_ENGINE_FRAME '+json.dumps(out))
