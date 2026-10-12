"""Read the current accepted M4 hand geometry and active idle grasps."""
from pathlib import Path
O=Path(__file__).parent
exec((O/'export_inputs.py').read_text().split('mesh,data=geometry(')[0])
mesh,data=geometry('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',True)
old=json.loads(gzip.decompress((O/'donor_profiles.json.gz').read_bytes()))
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
result={}
for family,entry in old.items():
    source=entry['idle'][0]['source'];clip=u.load_asset(source);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,opt)
    result[family]={'source':source,'time':0,'local':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['rest']}}
dump('M4_donors',result)
print('ACCEPTED_M4_DONORS_READY',flush=True)
