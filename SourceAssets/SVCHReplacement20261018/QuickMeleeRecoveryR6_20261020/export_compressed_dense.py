"""Read-only dense compressed source sampling; no scene or asset mutations."""
from pathlib import Path
import unreal as u,json,gzip,hashlib
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve()
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names());del mod
path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_quick_melee'
anim=u.load_asset(path);options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.COMPRESSED
def xf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
rate=1920;times=[i/rate for i in range(round(.9*rate)+1)];frames=[]
for t in times:
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,options)
    frames.append([xf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
with gzip.open(O/'compressed-1920.json.gz','wt') as f:json.dump({'path':path,'rate':rate,'names':[str(n) for n in names],'times':times,'frames':frames,
    'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()},f,separators=(',',':'))
print('SVCH_COMPRESSED_DENSE_EXPORTED',rate,len(frames),flush=True)
