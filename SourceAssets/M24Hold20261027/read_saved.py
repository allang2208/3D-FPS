"""Targeted saved-pose, unit and material readback for the reported M24 defects."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).resolve().parent;R='/Game/Weapons/M24/Hold20261027'
auth=json.loads((O/'authoring.json').read_text());receipt={'complete':False,'clips':{}}
mesh=u.load_asset(R+'/SK_M24_HoldV9');sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
settings=sk.get_lod_build_settings(mesh,0)
assert not settings.recompute_normals and not settings.recompute_tangents
assert settings.use_full_precision_u_vs and settings.use_high_precision_tangent_basis
ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
def pos(p,n):
    v=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD).translation
    return [v.x,v.y,v.z]
length=math.dist(pos(ref,'WPN_RearSight'),pos(ref,'WPN_FrontSight'))
assert 41<length<42
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
idle=None
for role,row in auth['clips'].items():
    clip=u.load_asset(R+'/Animations/A_M24_'+role)
    assert abs(clip.get_play_length()-row['duration'])<.001
    samples=[]
    for t in (0.,clip.get_play_length()*.5,clip.get_play_length()):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
        span=math.dist(pos(pose,'WPN_RearSight'),pos(pose,'WPN_FrontSight'))
        assert abs(span-length)<.02,(role,span)
        samples.append({n:pos(pose,n) for n in ('hand_l','hand_r','WPN_RearSight','WPN_FrontSight','WPN_BoltHandle','WPN_Magazine')})
    receipt['clips'][role]={'seconds':clip.get_play_length(),'samples':samples}
    if role=='idle':idle=samples[0]
errors={}
for n in ('hand_l','hand_r','WPN_RearSight','WPN_FrontSight'):
    source=auth['idle_bones'][n];expected=[source[0]*100,-source[1]*100,source[2]*100]
    errors[n]=math.dist(idle[n],expected)
assert max(errors.values())<.02,errors
receipt['idle_source_error_cm']=errors;receipt['sight_span_cm']=length
receipt['build_settings']=str(settings)
receipt['materials']=[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in mesh.materials]
receipt['returns_to_hold_cm']={role:{n:math.dist(row['samples'][-1][n],idle[n]) for n in ('hand_l','hand_r','WPN_RearSight')} for role,row in receipt['clips'].items()}
assert max(v for row in receipt['returns_to_hold_cm'].values() for v in row.values())<.02
receipt['complete']=True
(O/'saved_readback.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_HOLD_SAVED_READBACK',errors,len(receipt['clips']),flush=True)
