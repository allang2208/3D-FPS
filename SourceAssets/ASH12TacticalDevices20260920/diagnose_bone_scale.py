"""Focused user-requested imported pose scale check; no game session needed."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.AnimPoseExtensions
mesh=u.load_asset('/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
def v(p):return [p.x,p.y,p.z]
report={'mesh':mesh.get_path_name(),'viewmodel_scale':v(u.get_default_object(u.FPSGAMECharacter).get_editor_property('viewmodel_scale')),'poses':[]}
for name,path in [('idle','Integrated20260917/Animations'),('aim','Integrated20260917/Animations'),('reload','ReloadReference20260919')]:
    clip=u.load_asset('/Game/Weapons/ASH12/'+path+'/A_ASH12_'+name)
    for time in (0.,clip.get_play_length()*.5):
        p=E.get_anim_pose_at_time(clip,time,opts)
        root=E.get_ref_bone_pose(p,'WPN_root',u.AnimPoseSpaces.WORLD)
        current=E.get_bone_pose(p,'WPN_root',u.AnimPoseSpaces.WORLD)
        relative=u.MathLibrary.make_relative_transform(u.Transform(),root)
        resolved=relative.scale3d*current.scale3d
        report['poses'].append({'clip':name,'time':time,'root_reference_scale':v(root.scale3d),
            'root_animated_scale':v(current.scale3d),'attachment_relative_scale':v(relative.scale3d),'effective_mesh_scale':v(resolved)})
(O/'bone_scale.json').write_text(json.dumps(report,indent=2))
print('ASH_TACTICAL_BONE_SCALE '+json.dumps(report))
