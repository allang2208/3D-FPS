"""Read the native palm mounts, planted pose and heavy-landing pose for each body."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
cfg=json.loads((P.parents[1]/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
ext=u.AnimPoseExtensions
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
out={}
for key,body in [('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    mesh=u.load_asset(body['body_mesh'])
    sk=mesh.get_editor_property('skeleton')
    ref=ext.get_reference_pose(sk)
    comp=u.new_object(u.SkeletalMeshComponent)
    comp.set_skeletal_mesh_asset(mesh)
    names=[str(n) for n in ext.get_bone_names(ref)]
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh
    opts.evaluation_type=u.AnimDataEvalType.SOURCE
    idle=u.load_asset(body['clips']['Melee.FullBody.Idle'])
    heavy=u.load_asset(body['clips']['Melee.FullBody.HeavyRelease'])
    ts={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(heavy)}
    sample=lambda a,t:ext.get_anim_pose_at_time(a,t,opts)
    poses={'ref':ref,'idle':sample(idle,0.),'land':sample(heavy,ts.get('Release',heavy.get_play_length()*.5))}
    out[key]={'names':names,'parents':[str(comp.get_parent_bone(n)) for n in names],
              'skeleton':sk.get_path_name(),'body':mesh.get_path_name(),
              **{k:{n:pack(ext.get_bone_pose(v,n,u.AnimPoseSpaces.LOCAL)) for n in names} for k,v in poses.items()}}
(P/'body-anchors.json').write_text(json.dumps(out,separators=(',',':')))
